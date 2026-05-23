# app/agent/core.py

import asyncio

from app.agent.intent import detect_intent
from app.agent.memory import get_history, add_message
from app.agent.workflow_executor import (
    run_workflow,
    run_workflow_stream,
)

from app.model.sse import SSEEvent
from app.utils import setup_logger

logger = setup_logger("Agent Core")

class AgentCore:

    def __init__(self):
        pass

    # =========================
    # 普通模式（非流式）
    # =========================
    async def run(self, user_input: str, session_id: str = "default_session"):
        # 1. 意图识别
        workflow_name = await detect_intent(user_input)

        # 2. 记录用户消息
        add_message("user", user_input, session_id)

        # 3. 获取历史记录
        history = get_history(session_id)

        # 4. 执行工作流
        wf_result = await run_workflow(
            user_input=user_input,
            history=history,
            intent=workflow_name,
        )

        answer = (
            wf_result.get("answer")
            or "抱歉，我暂时无法回答这个问题，请再试一次。"
        )

        # 5. 保存 assistant 回复
        if wf_result.get("answer"):
            add_message("assistant", answer, session_id)

        # 6. 返回结果
        return {
            "intent": wf_result.get("intent", workflow_name),
            "answer": answer,
            "steps": wf_result.get("steps", []),
        }

    # =========================
    # 流式模式（SSE）
    # =========================
    async def stream(self, user_input: str, session_id: str = "default_session"):

        # 用户消息
        yield SSEEvent(
            event="user_message",
            content=user_input,
        ).model_dump()

        # 开始规划
        yield SSEEvent(
            event="planner_start",
            content="正在规划工作流...",
        ).model_dump()

        await asyncio.sleep(0)

        # 意图识别
        workflow_name = await detect_intent(user_input)

        yield SSEEvent(
            event="intent_detected",
            content=f"识别意图: {workflow_name}",
            data={
                "intent": workflow_name,
            }
        ).model_dump()

        # 保存用户消息
        add_message("user", user_input, session_id)

        # 加载历史
        history = get_history(session_id)

        yield SSEEvent(
            event="history_loaded",
            content=f"已加载 {len(history)} 条历史记录",
            data={
                "count": len(history),
            }
        ).model_dump()

        # 执行工作流
        final_answer = ""

        async for event in run_workflow_stream(
            user_input=user_input,
            history=history,
            intent=workflow_name,
        ):

            # 保存最终回答
            if event["event"] == "final":

                final_answer = (
                    event.get("data", {})
                    .get("answer", "")
                )

            yield event

        # 保存 assistant 回复
        if final_answer:
            add_message("assistant", final_answer, session_id)