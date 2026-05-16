# app/agent/workflow_executor.py
import json
import logging
from app.agent.tools import run_tool
from app.agent.planner import plan_steps
from app.rag import retrieve
from app.llm.llm_client import chat_with_llm

logger = logging.getLogger(__name__)


async def run_workflow(user_input: str, history: list) -> dict:
    """
    执行动态工作流
    """
    logger.info(f"[Workflow] 用户输入: {user_input}")

    # 始终使用动态规划
    steps = plan_steps(user_input)
    
    # 初始化上下文
    context = {
        "user_input": user_input,
        "history": history,
        "docs": [],
        "tool_result": None,
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

                context["tool_result"] = result
                steps_output.append({"type": "tool", "tool": tool_name, "output": result})

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
                    tool_result=context.get("tool_result"),
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