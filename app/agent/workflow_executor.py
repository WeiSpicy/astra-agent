# app/agent/workflow_executor.py
import json
from app.agent.tools import run_tool
from app.agent.planner import plan_steps
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
    steps = plan_steps(user_input)

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


async def run_workflow_stream(user_input: str, history: list):
    """
    流式执行动态工作流，返回标准化 SSEEvent
    """
    logger.info(f"开始处理: {user_input}")

    # Step 1: 规划阶段
    yield SSEEvent(event="status", content="正在规划执行步骤...").model_dump()

    steps = plan_steps(user_input)

    yield SSEEvent(
        event="steps", content="规划完成", data={"steps": steps}
    ).model_dump()

    # 初始化上下文
    context = {
        "user_input": user_input,
        "history": history,
        "docs": [],
        "tool_results_map": [],
        "llm_result": None,
    }

    # Step 2: 逐个执行步骤
    for i, step in enumerate(steps):
        step_type = step.get("type")

        yield SSEEvent(
            event="step_start",
            content=f"正在执行步骤 {i+1}/{len(steps)}: {step_type}",
            data={"step": step, "index": i},
        ).model_dump()

        try:
            if step_type == "tool":
                tool_name = step.get("tool") or step.get("name")
                args = step.get("args") or {}

                yield SSEEvent(
                    event="tool_start",
                    content=f"正在调用工具: {tool_name}",
                    data={"tool": tool_name},
                ).model_dump()

                tool_input = json.dumps({"tool": tool_name, "args": args})
                result = run_tool(tool_input)

                context["tool_results_map"].append(
                    {"tool": tool_name, "args": args, "result": result}
                )

                yield SSEEvent(
                    event="tool_result",
                    content=f"工具 {tool_name} 执行完成",
                    data={"tool": tool_name, "output": result},
                ).model_dump()

            elif step_type == "rag":
                query = step.get("query") or user_input
                yield SSEEvent(
                    event="rag_start",
                    content="正在检索知识库...",
                    data={"query": query},
                ).model_dump()

                docs = retrieve(query)
                context["docs"] = docs

                yield SSEEvent(
                    event="rag_result",
                    content=f"检索完成，找到 {len(docs)} 条相关内容",
                    data={"query": query, "docs_count": len(docs)},
                ).model_dump()

            elif step_type == "llm":

                yield SSEEvent(
                    event="llm_start",
                    content="正在生成最终回答...",
                ).model_dump()

                prompt = step.get("prompt", "")
                full_answer = ""
                tool_result = context.get("tool_results_map", [])
                tool_result_str = json.dumps(
                    tool_result,
                    ensure_ascii=False,
                    indent=2
                )
                async for event in stream_chat_llm(
                    user_input=f"{prompt}\n当前用户问题: {context['user_input']}",
                    history=context["history"],
                    context_docs=context.get("docs", []),
                    tool_result=tool_result_str,
                ):

                    # token
                    if event["event"] == "token":

                        full_answer += event["content"]

                        yield event

                    # done
                    elif event["event"] == "done":
                        context["llm_result"] = full_answer

                    # error
                    elif event["event"] == "error":
                        yield event

        except Exception as e:
            logger.exception(f"步骤执行失败: {step_type}")
            yield SSEEvent(
                event="error",
                content=f"步骤执行失败: {str(e)}",
                data={"step_type": step_type},
            ).model_dump()
            break

    # Step 3: 最终结果
    final_answer = context.get("llm_result") or "工作流执行完成"
    yield SSEEvent(
        event="final", content=final_answer, data={"answer": final_answer}
    ).model_dump()
