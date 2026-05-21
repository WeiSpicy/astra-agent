# app/agent/workflow_executor.py
import asyncio
import json
from app.agent.tools import run_tool
from app.agent.planner import plan_steps_async
from app.model.sse import SSEEvent
from app.rag import retrieve
from app.llm.llm_client import chat_with_llm
from app.llm.stream_llm import stream_chat_llm
from app.utils import setup_logger

logger = setup_logger("Agent workflow")


async def run_workflow(user_input: str, history: list) -> dict:
    """
    执行动态工作流
    """
    logger.info(f"用户输入: {user_input}")

    # 始终使用动态规划
    steps = await plan_steps_async(user_input)

    # 初始化上下文
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
                tool_input = json.dumps({"tool": tool_name, "args": args})
                result = run_tool(tool_input)

                context["tool_results_map"].append(
                    {"tool": tool_name, "args": args, "result": result}
                )
                steps_output.append(
                    {"type": "tool", "tool": tool_name, "output": result}
                )

            elif step_type == "rag":
                query = step.get("query") or user_input
                docs = retrieve(query)
                context["docs"] = docs
                steps_output.append({"type": "rag", "query": query, "output": docs})

            elif step_type == "llm":
                prompt = step.get("prompt", "")
                answer = chat_with_llm(
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
        "intent": "dynamic",
        "answer": context.get("llm_result") or "工作流执行完成",
        "steps": steps_output,
        "success": context.get("llm_result") is not None,
    }

TOOL_DESC = {
    "now": lambda args: "查询当前时间",
    "weather": lambda args: f"查询{args.get('city','未知')}天气",
    "calc": lambda args: f"计算 {args.get('expr','')}",
}

async def run_workflow_stream(user_input: str, history: list):
    """
    流式执行动态工作流（支持同步工具/RAG底层无痛并行化改造 + 异步队列流式状态感知）
    """
    logger.info(f"开始处理复合意图: {user_input}")

    # Step 1: 规划阶段
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
    
    # 创建异步队列, 用于子协程向主线程实时 “打小报告”
    event_queue = asyncio.Queue()

    # 2.1 封装同步工具的并行 Worker
    async def worker_tool(step_dict: dict, idx: int):
        tool_name = step_dict.get("tool") or step_dict.get("name")
        args = step_dict.get("args") or {}
        desc = TOOL_DESC[tool_name](args) if tool_name in TOOL_DESC else ""
        
        # 触发时立即丢进队列, 前端秒级感知
        await event_queue.put(f"[Tool] 开始调用工具 [{tool_name}] {desc}")

        tool_input_str = json.dumps({"tool": tool_name, "args": args})

        # 利用 asyncio.to_thread 丢进后台独立线程, 实现真正并行
        result = await asyncio.to_thread(run_tool, tool_input_str)

        context["tool_results_map"].append(
            {"tool": tool_name, "args": args, "result": result}
        )
        
        # 执行完立即丢进队列
        await event_queue.put(f"[Tool] 工具 [{tool_name}] 执行完成")

    # 2.2 封装同步 RAG 的并行 Worker
    async def worker_rag(step_dict: dict):
        query = step_dict.get("query") or user_input
        await event_queue.put(f"[RAG] 知识库开始检索: '{query}'...")

        # 利用 to_thread 让同步 RAG 检索在后台并发运行
        docs = await asyncio.to_thread(retrieve, query)
        context["docs"].extend(docs)

        await event_queue.put(f"[RAG] 知识库检索完成, 找到 {len(docs)} 条相关文档")

    # 2.3 扫描解析规划步骤, 将其装载进并发任务池中
    has_llm_step = False
    for i, step in enumerate(steps):
        step_type = step.get("type")
        if step_type == "tool":
            tasks.append(worker_tool(step, i))
        elif step_type == "rag":
            tasks.append(worker_rag(step))
        elif step_type == "llm":
            has_llm_step = True

    # 2.4 并发任务与抢占式通知
    if tasks:
        yield SSEEvent(
            event="status", 
            content=f"已并行触发 {len(tasks)} 个本地任务..."
        ).model_dump()
        
        # 将所有并行任务捆绑打包
        bg_tasks = asyncio.gather(*tasks)
        
        # 只要后台并发任务没全部完成, 或者队列里还有未消化的状态, 就持续监听
        while not bg_tasks.done() or not event_queue.empty():
            try:
                # 设置一个极短的超时, 防止队列没消息时主线程死等导致事件流卡住
                msg = await asyncio.wait_for(event_queue.get(), timeout=0.1)
                yield SSEEvent(event="status", content=msg).model_dump()
                event_queue.task_done()
            except asyncio.TimeoutError:
                # 暂时没有新事件, 让出控制权稍微歇一下
                await asyncio.sleep(0.02)
        
        # 如果发生内部异常, 会在此时抛出
        await bg_tasks

    # Step 3: 总结
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

    # ==========================================
    # Step 4: 谢幕
    # ==========================================
    final_answer = context.get("llm_result") or "工作流执行完成"
    yield SSEEvent(
        event="final", content=final_answer, data={"answer": final_answer}
    ).model_dump()