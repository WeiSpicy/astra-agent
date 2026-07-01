# app/agent/workflow_executor.py
import asyncio
import json
from app.agent.tools import execute_tool
from app.agent.planner import plan_steps_async
from app.model.sse import SSEEvent
from app.rag import retrieve
from app.llm.llm_client import chat_with_llm
from app.llm.stream_llm import stream_chat_llm
from app.utils import setup_logger

logger = setup_logger("Agent workflow")


async def run_workflow(user_input: str, history: list, intent: str = "dynamic") -> dict:
    logger.info(f"用户输入: {user_input}, 意图: {intent}")

    if intent == "chat":
        answer = await asyncio.to_thread(
            chat_with_llm,
            user_input=user_input, history=history, context_docs=[], tool_result=[],
        )
        return {
            "intent": "chat",
            "answer": answer,
            "steps": [{"type": "llm", "output": answer}],
            "success": bool(answer),
        }

    if intent == "rag":
        docs = await asyncio.to_thread(retrieve, user_input)
        answer = await asyncio.to_thread(
            chat_with_llm,
            user_input=user_input, history=history, context_docs=docs, tool_result=[],
        )
        return {
            "intent": "rag",
            "answer": answer,
            "steps": [
                {"type": "rag", "query": user_input, "output": docs},
                {"type": "llm", "output": answer},
            ],
            "success": bool(answer),
        }

    steps = await plan_steps_async(user_input)

    if not steps:
        steps = [{"type": "llm", "prompt": f"直接回答用户问题: {user_input}"}]

    context = {
        "user_input": user_input,
        "history": history,
        "docs": [],
        "tool_results_map": [],
        "llm_result": None,
    }
    steps_output = []

    for step in steps:
        step_type = step.get("type")
        if not step_type:
            continue

        try:
            if step_type == "tool":
                tool_name = step.get("tool") or step.get("name")
                args = step.get("args") or {}
                result = await asyncio.to_thread(execute_tool, tool_name, args)

                context["tool_results_map"].append(
                    {"tool": tool_name, "args": args, "result": result}
                )
                steps_output.append(
                    {"type": "tool", "tool": tool_name, "output": result}
                )

            elif step_type == "rag":
                query = step.get("query") or user_input
                docs = await asyncio.to_thread(retrieve, query)
                context["docs"] = docs
                steps_output.append({"type": "rag", "query": query, "output": docs})

            elif step_type == "llm":
                prompt = step.get("prompt", "")
                answer = await asyncio.to_thread(
                    chat_with_llm,
                    user_input=f"{prompt}\n当前用户问题: {context['user_input']}",
                    history=context["history"],
                    context_docs=context.get("docs", []),
                    tool_result=context.get("tool_results_map"),
                )
                context["llm_result"] = answer
                steps_output.append({"type": "llm", "output": answer})

        except Exception as e:
            logger.exception(f"步骤执行失败: {step_type}")
            steps_output.append({"type": step_type, "error": str(e)})
            break

    return {
        "intent": intent,
        "answer": context.get("llm_result") or "工作流执行完成",
        "steps": steps_output,
        "success": context.get("llm_result") is not None,
    }

TOOL_DESC = {
    "now": lambda _: "查询当前时间",
    "weather": lambda args: f"查询{args.get('city','未知')}天气",
    "calc": lambda args: f"计算 {args.get('expression','')}",
}

async def _stream_llm_answer(user_input: str, history: list, context_docs: list, tool_result, intent_label: str):
    full_answer = ""
    try:
        async for event in stream_chat_llm(
            user_input=user_input, history=history,
            context_docs=context_docs, tool_result=tool_result,
        ):
            if event["event"] == "token":
                full_answer += event["content"]
                yield event
            elif event["event"] == "done":
                pass
            elif event["event"] == "error":
                yield event
    except Exception as e:
        logger.exception(f"{intent_label} 流式生成失败")
        yield SSEEvent(event="error", content=f"生成失败: {str(e)}").model_dump()

    yield SSEEvent(
        event="final", content=full_answer,
        data={"answer": full_answer, "intent": intent_label}
    ).model_dump()


async def run_workflow_stream(user_input: str, history: list, intent: str = "dynamic"):
    logger.info(f"开始处理意图 [{intent}]: {user_input}")

    if intent == "chat":
        yield SSEEvent(event="status", content="正在生成回复...").model_dump()
        async for event in _stream_llm_answer(user_input, history, [], [], "chat"):
            yield event
        return

    if intent == "rag":
        yield SSEEvent(event="status", content="正在检索知识库...").model_dump()
        docs = await asyncio.to_thread(retrieve, user_input)
        yield SSEEvent(event="status", content=f"知识库检索完成, 找到 {len(docs)} 条相关文档").model_dump()
        yield SSEEvent(event="llm_start", content="正在生成回答...").model_dump()
        async for event in _stream_llm_answer(user_input, history, docs, [], "rag"):
            yield event
        return

    yield SSEEvent(event="status", content="正在规划执行步骤...").model_dump()

    steps = await plan_steps_async(user_input)

    yield SSEEvent(
        event="steps", content="规划完成", data={"steps": steps}
    ).model_dump()

    # 初始化运行时上下文
    context = {
        "user_input": user_input,
        "history": history,
        "docs": [],
        "tool_results_map": [],
        "llm_result": None,
    }

    # Step 2: 任务分桶与多线程并行执行 (Async Queue)
    tasks = []
    
    event_queue = asyncio.Queue()

    async def worker_tool(step_dict: dict):
        tool_name = step_dict.get("tool") or step_dict.get("name")
        args = step_dict.get("args") or {}
        desc = TOOL_DESC[tool_name](args) if tool_name in TOOL_DESC else ""

        await event_queue.put(f"[Tool] 开始调用工具 [{tool_name}] {desc}")

        result = await asyncio.to_thread(execute_tool, tool_name, args)

        context["tool_results_map"].append(
            {"tool": tool_name, "args": args, "result": result}
        )
        
        await event_queue.put(f"[Tool] 工具 [{tool_name}] 执行完成")

    async def worker_rag(step_dict: dict):
        query = step_dict.get("query") or user_input
        await event_queue.put(f"[RAG] 知识库开始检索: '{query}'...")

        docs = await asyncio.to_thread(retrieve, query)
        context["docs"].extend(docs)

        await event_queue.put(f"[RAG] 知识库检索完成, 找到 {len(docs)} 条相关文档")

    # 2.3 并发执行任务步骤
    has_llm_step = False
    for step in steps:
        step_type = step.get("type")
        if step_type == "tool":
            tasks.append(worker_tool(step))
        elif step_type == "rag":
            tasks.append(worker_rag(step))
        elif step_type == "llm":
            has_llm_step = True

    # 2.4 并发任务执行与事件推送
    if tasks:
        yield SSEEvent(
            event="status", 
            content=f"已并行触发 {len(tasks)} 个本地任务..."
        ).model_dump()
        
        bg_tasks = asyncio.gather(*tasks)
        
        while not bg_tasks.done() or not event_queue.empty():
            try:
                # 设置一个极短的超时, 防止队列没消息时主线程死等导致事件流卡住
                msg = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                yield SSEEvent(event="status", content=msg).model_dump()
                event_queue.task_done()
            except asyncio.TimeoutError:
                await asyncio.sleep(0.02)
        
        await bg_tasks

    # Step 3: 基于工具结果生成总结
    if has_llm_step:
        yield SSEEvent(
            event="llm_start",
            content="正在生成最终回答...",
        ).model_dump()

        system_guide = (
            "你是一个聪明且友好的AI助手。请结合给出的『工具执行结果』或『检索到的知识库文档』, "
            "严格、专业且有条理地回答用户的『当前原始问题』。如果用户设置了某些前提条件（如具体的日期、特定城市等）, "
            "请根据工具返回的真实数据进行逻辑判断后再做应答。"
            "[知识边界协议]:"
            "1. 优先使用『工具执行结果』和『知识库文档』回答问题。"
            "2. 如果提供的信息中未包含相关资料, 必须明确告知用户：'目前我的知识库里没有收录相关的资料'。"
            "3. 在告知前提后, 允许你以通用知识为基础进行补充说明。"
            "4. 如果是日常问候、闲聊、或询问你的身份/名字，请直接友好地回答，不需要提示知识库缺失。"
        )

        tool_result_str = json.dumps(context["tool_results_map"], ensure_ascii=False, indent=2)
        full_answer = ""
        
        try:
            async for event in stream_chat_llm(
                user_input=f"{system_guide}\n\n当前用户原始问题: {context['user_input']}",
                history=context["history"],
                context_docs=context.get("docs", []),
                tool_result=tool_result_str,
            ):
                if event["event"] == "token":
                    full_answer += event["content"]
                    yield event
                elif event["event"] == "done":
                    context["llm_result"] = full_answer
                elif event["event"] == "error":
                    yield event
        except Exception as e:
            logger.exception("大模型最终总结生成失败")
            yield SSEEvent(event="error", content=f"总结生成失败: {str(e)}").model_dump()

    # Step 4: 生成最终回复
    final_answer = context.get("llm_result") or "工作流执行完成"
    yield SSEEvent(
        event="final", content=final_answer, data={"answer": final_answer}
    ).model_dump()