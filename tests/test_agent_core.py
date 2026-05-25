from unittest.mock import patch
from app.agent.core import AgentCore
from app.agent.memory import get_history, clear_all_histories


class TestAgentCoreRun:
    async def test_run_chat_workflow_returns_answer(self):
        """完整 run 链路：意图识别 → 工作流 → 回答"""
        core = AgentCore()
        clear_all_histories()

        with (
            patch("app.agent.core.detect_intent") as mock_intent,
            patch("app.agent.core.run_workflow") as mock_wf,
        ):
            mock_intent.return_value = "chat"
            mock_wf.return_value = {
                "intent": "chat",
                "answer": "你好！",
                "steps": [{"type": "llm", "output": "你好！"}],
                "success": True,
            }

            result = await core.run("你好", session_id="test_session")

            mock_intent.assert_called_once_with("你好")
            mock_wf.assert_called_once()
            assert result["intent"] == "chat"
            assert result["answer"] == "你好！"

    async def test_run_saves_messages_to_memory(self):
        """用户消息和助手回复都被存入记忆"""
        core = AgentCore()
        clear_all_histories()

        with (
            patch("app.agent.core.detect_intent") as mock_intent,
            patch("app.agent.core.run_workflow") as mock_wf,
        ):
            mock_intent.return_value = "chat"
            mock_wf.return_value = {
                "intent": "chat",
                "answer": "你好！",
                "steps": [],
                "success": True,
            }

            await core.run("你好", session_id="mem_test")

            history = get_history("mem_test")
            assert len(history) == 2
            assert history[0] == {"role": "user", "content": "你好"}
            assert history[1] == {"role": "assistant", "content": "你好！"}

    async def test_run_fallback_when_answer_empty(self):
        """工作流返回空回答时使用兜底文案"""
        core = AgentCore()
        clear_all_histories()

        with (
            patch("app.agent.core.detect_intent") as mock_intent,
            patch("app.agent.core.run_workflow") as mock_wf,
        ):
            mock_intent.return_value = "dynamic"
            mock_wf.return_value = {
                "intent": "dynamic",
                "answer": None,
                "steps": [{"type": "tool", "error": "超时"}],
                "success": False,
            }

            result = await core.run("帮我查天气", session_id="fb_test")

            assert "抱歉" in result["answer"]

    async def test_run_different_sessions_isolated(self):
        """不同 session 的记忆互相隔离"""
        core = AgentCore()
        clear_all_histories()

        with (
            patch("app.agent.core.detect_intent") as mock_intent,
            patch("app.agent.core.run_workflow") as mock_wf,
        ):
            mock_intent.return_value = "chat"
            mock_wf.return_value = {
                "intent": "chat", "answer": "OK", "steps": [], "success": True
            }

            await core.run("A", session_id="session_1")
            await core.run("B", session_id="session_2")

            h1 = get_history("session_1")
            h2 = get_history("session_2")
            assert h1[0]["content"] == "A"
            assert h2[0]["content"] == "B"

    async def test_run_passes_history_to_workflow(self):
        """工作流收到的 history 包含之前的对话"""
        core = AgentCore()
        clear_all_histories()

        with (
            patch("app.agent.core.detect_intent") as mock_intent,
            patch("app.agent.core.run_workflow") as mock_wf,
        ):
            mock_intent.return_value = "chat"
            mock_wf.return_value = {
                "intent": "chat", "answer": "北京是中国的首都",
                "steps": [], "success": True
            }

            # 第一轮
            await core.run("中国首都是哪里", session_id="history_test")
            # 第二轮：追问
            await core.run("那里有多少人口", session_id="history_test")

            # 验证第二轮调用时传入了第一轮的历史
            call_args = mock_wf.call_args_list[1]
            history_passed = call_args.kwargs["history"]
            assert len(history_passed) >= 2


class TestAgentCoreStream:
    async def test_stream_yields_user_and_intent_events(self):
        """流式输出包含 user_message 和 intent_detected 事件"""
        core = AgentCore()
        clear_all_histories()

        with (
            patch("app.agent.core.detect_intent") as mock_intent,
            patch("app.agent.core.run_workflow_stream") as mock_wf_stream,
        ):
            mock_intent.return_value = "chat"
            mock_wf_stream.return_value = aiter_from_list([
                {"event": "status", "content": "正在生成回复..."},
                {"event": "token", "content": "你好"},
                {"event": "final", "content": "你好！",
                 "data": {"answer": "你好！", "intent": "chat"}},
            ])

            events = [
                e async for e in core.stream("你好", session_id="stream_test")
            ]

            event_types = [e["event"] for e in events]
            assert "user_message" in event_types
            assert "planner_start" in event_types
            assert "intent_detected" in event_types
            assert "token" in event_types
            assert "final" in event_types

    async def test_stream_saves_assistant_message(self):
        """流式完成后助手回复被保存到记忆"""
        core = AgentCore()
        clear_all_histories()

        with (
            patch("app.agent.core.detect_intent") as mock_intent,
            patch("app.agent.core.run_workflow_stream") as mock_wf_stream,
        ):
            mock_intent.return_value = "chat"
            mock_wf_stream.return_value = aiter_from_list([
                {"event": "final", "content": "你好！",
                 "data": {"answer": "你好！", "intent": "chat"}},
            ])

            async for _ in core.stream("你好", session_id="stream_mem_test"):
                pass

            history = get_history("stream_mem_test")
            assert len(history) == 2
            assert history[1] == {"role": "assistant", "content": "你好！"}

    async def test_stream_no_final_event_no_save(self):
        """没有 final 事件时不保存空的助手消息"""
        core = AgentCore()
        clear_all_histories()

        with (
            patch("app.agent.core.detect_intent") as mock_intent,
            patch("app.agent.core.run_workflow_stream") as mock_wf_stream,
        ):
            mock_intent.return_value = "chat"
            mock_wf_stream.return_value = aiter_from_list([
                {"event": "error", "content": "服务异常"},
            ])

            async for _ in core.stream("你好", session_id="no_final_test"):
                pass

            history = get_history("no_final_test")
            # 只保存了用户消息，没有助手消息
            assert len(history) == 1
            assert history[0]["role"] == "user"


def aiter_from_list(items):
    async def _gen():
        for item in items:
            yield item
    return _gen()
