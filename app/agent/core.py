# app/agent/core.py
import asyncio

from app.agent.intent import detect_intent
from app.agent.memory import get_history, add_message
from app.agent.workflow_executor import run_workflow, run_workflow_stream

class AgentCore:
    def __init__(self):
        pass

    async def run(self, user_input: str):
        # 1. 意图识别
        workflow_name = detect_intent(user_input)

        # 先记录用户消息
        add_message("user", user_input)   # 每次用户说话都记录

        # 2. 获取历史
        history = get_history()

        # 3. 执行工作流
        wf_result = await run_workflow(
            user_input=user_input,
            history=history
        )

        answer = wf_result.get("answer") or "抱歉，我暂时无法回答这个问题，请再试一次。"

        # 4. 记忆管理
        # 只有真正有意义的回答才记录（避免记录默认错误提示）
        if wf_result.get("answer"):       # 关键：看原始返回里是否有 answer
            add_message("assistant", answer)

        # 5. 返回结果
        return {
            "intent": wf_result.get("intent", workflow_name),
            "answer": answer,
            "steps": wf_result.get("steps", []),
        }
        
    async def stream(self, user_input: str):

        yield {
            "event": "user_message",
            "data": {
                "content": user_input
            }
        }

        yield {
            "event": "planner_start",
            "data": {
                "message": "正在规划工作流..."
            }
        }

        await asyncio.sleep(0)

        workflow_name = detect_intent(user_input)

        yield {
            "event": "intent_detected",
            "data": {
                "intent": workflow_name
            }
        }

        add_message("user", user_input)

        history = get_history()

        yield {
            "event": "history_loaded",
            "data": {
                "count": len(history)
            }
        }

        async for event in run_workflow_stream(
            user_input=user_input,
            history=history,
        ):
            yield event