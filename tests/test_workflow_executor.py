from unittest.mock import patch
from app.agent.workflow_executor import run_workflow, run_workflow_stream


class TestRunWorkflow:
    async def test_chat_intent_calls_llm_directly(self):
        """闲聊意图：跳过工具和 RAG，直接调 LLM"""
        with patch("app.agent.workflow_executor.chat_with_llm") as mock_llm:
            mock_llm.return_value = "你好，有什么可以帮你？"

            result = await run_workflow(
                user_input="你好", history=[], intent="chat"
            )

            mock_llm.assert_called_once()
            assert result["intent"] == "chat"
            assert result["answer"] == "你好，有什么可以帮你？"
            assert result["success"] is True

    async def test_rag_intent_retrieves_then_calls_llm(self):
        """RAG 意图：先检索知识库，再调 LLM 生成回答"""
        with (
            patch("app.agent.workflow_executor.retrieve") as mock_retrieve,
            patch("app.agent.workflow_executor.chat_with_llm") as mock_llm,
        ):
            mock_retrieve.return_value = [{"content": "FastAPI 是一个 Web 框架"}]
            mock_llm.return_value = "FastAPI 是一个高性能的 Python Web 框架"

            result = await run_workflow(
                user_input="什么是 FastAPI", history=[], intent="rag"
            )

            mock_retrieve.assert_called_once_with("什么是 FastAPI")
            mock_llm.assert_called_once()
            assert result["intent"] == "rag"
            assert "FastAPI" in result["answer"]

    async def test_rag_intent_no_docs_found(self):
        """RAG 意图：知识库无结果时 LLM 仍被调用"""
        with (
            patch("app.agent.workflow_executor.retrieve") as mock_retrieve,
            patch("app.agent.workflow_executor.chat_with_llm") as mock_llm,
        ):
            mock_retrieve.return_value = []
            mock_llm.return_value = "知识库中没有相关信息"

            result = await run_workflow(
                user_input="什么是 XYZ", history=[], intent="rag"
            )

            mock_llm.assert_called_once()
            assert result["success"] is True

    async def test_dynamic_executes_tool_then_llm(self):
        """动态工作流：规划出 tool → llm 两步，验证执行顺序"""
        with (
            patch("app.agent.workflow_executor.plan_steps_async") as mock_plan,
            patch("app.agent.workflow_executor.execute_tool") as mock_tool,
            patch("app.agent.workflow_executor.chat_with_llm") as mock_llm,
        ):
            mock_plan.return_value = [
                {"type": "tool", "tool": "calc", "args": {"expression": "1+1"}},
                {"type": "llm"},
            ]
            mock_tool.return_value = {"result": 2}
            mock_llm.return_value = "计算结果为 2"

            result = await run_workflow(
                user_input="1+1等于多少", history=[], intent="dynamic"
            )

            mock_plan.assert_called_once_with("1+1等于多少")
            mock_tool.assert_called_once_with("calc", {"expression": "1+1"})
            mock_llm.assert_called_once()
            assert result["answer"] == "计算结果为 2"
            assert result["success"] is True

    async def test_dynamic_executes_rag_then_llm(self):
        """动态工作流：规划出 rag → llm 两步"""
        with (
            patch("app.agent.workflow_executor.plan_steps_async") as mock_plan,
            patch("app.agent.workflow_executor.retrieve") as mock_retrieve,
            patch("app.agent.workflow_executor.chat_with_llm") as mock_llm,
        ):
            mock_plan.return_value = [
                {"type": "rag", "query": "Python GIL"},
                {"type": "llm"},
            ]
            mock_retrieve.return_value = [{"content": "GIL 是全局解释器锁"}]
            mock_llm.return_value = "GIL 的作用是..."

            result = await run_workflow(
                user_input="解释一下 GIL", history=[], intent="dynamic"
            )

            mock_retrieve.assert_called_once_with("Python GIL")
            mock_llm.assert_called_once()
            assert result["success"] is True

    async def test_tool_failure_is_caught_not_crashed(self):
        """工具执行失败不会崩溃，错误记录在 steps 中"""
        with (
            patch("app.agent.workflow_executor.plan_steps_async") as mock_plan,
            patch("app.agent.workflow_executor.execute_tool") as mock_tool,
        ):
            mock_plan.return_value = [
                {"type": "tool", "tool": "calc", "args": {"expression": "1/0"}},
            ]
            mock_tool.side_effect = RuntimeError("计算失败")

            result = await run_workflow(
                user_input="1/0等于多少", history=[], intent="dynamic"
            )

            assert result["steps"][0].get("error") is not None
            assert result["success"] is False

    async def test_unknown_step_type_is_skipped(self):
        """未知步骤类型被跳过，不影响后续步骤"""
        with (
            patch("app.agent.workflow_executor.plan_steps_async") as mock_plan,
            patch("app.agent.workflow_executor.execute_tool") as mock_tool,
            patch("app.agent.workflow_executor.chat_with_llm") as mock_llm,
        ):
            mock_plan.return_value = [
                {"type": "unknown_xxx"},
                {"type": "tool", "tool": "now", "args": {}},
                {"type": "llm"},
            ]
            mock_tool.return_value = {"datetime": "2025-01-01"}
            mock_llm.return_value = "当前时间是 2025-01-01"

            result = await run_workflow(
                user_input="现在几点", history=[], intent="dynamic"
            )

            mock_tool.assert_called_once()
            assert result["success"] is True

    async def test_steps_without_type_key_are_skipped(self):
        """缺少 type 字段的步骤被安全跳过"""
        with (
            patch("app.agent.workflow_executor.plan_steps_async") as mock_plan,
            patch("app.agent.workflow_executor.chat_with_llm") as mock_llm,
        ):
            mock_plan.return_value = [
                {},
                {"type": "llm"},
            ]
            mock_llm.return_value = "你好"

            result = await run_workflow(
                user_input="你好", history=[], intent="dynamic"
            )

            assert result["success"] is True

    async def test_empty_steps_triggers_executor_fallback(self):
        """planner 返回空数组时 executor 兜底为 llm 步骤"""
        with (
            patch("app.agent.workflow_executor.plan_steps_async") as mock_plan,
            patch("app.agent.workflow_executor.chat_with_llm") as mock_llm,
        ):
            mock_plan.return_value = []
            mock_llm.return_value = "你好，有什么可以帮你的？"

            result = await run_workflow(
                user_input="?", history=[], intent="dynamic"
            )

            mock_llm.assert_called_once()
            assert result["steps"][0]["type"] == "llm"
            assert result["success"] is True
            assert "帮你" in result["answer"]

class TestRunWorkflowStream:
    async def test_stream_chat_intent_yields_final_event(self):
        """闲聊意图流式输出：产生 status 事件并以 final 结束"""
        with patch("app.agent.workflow_executor.stream_chat_llm") as mock_stream:
            mock_stream.return_value = aiter_from_list([
                {"event": "token", "content": "你好"},
                {"event": "token", "content": "！"},
                {"event": "done", "content": "你好！"},
            ])

            events = [
                e async for e in run_workflow_stream("你好", [], "chat")
            ]

            event_types = [e["event"] for e in events]
            assert "status" in event_types
            assert "token" in event_types
            final_events = [e for e in events if e["event"] == "final"]
            assert len(final_events) == 1

    async def test_stream_rag_intent_retrieves_then_streams(self):
        """RAG 意图流式：先发检索状态，再流式输出 LLM 回答"""
        with (
            patch("app.agent.workflow_executor.retrieve") as mock_retrieve,
            patch("app.agent.workflow_executor.stream_chat_llm") as mock_stream,
        ):
            mock_retrieve.return_value = [{"content": "GIL 文档"}]
            mock_stream.return_value = aiter_from_list([
                {"event": "token", "content": "GIL"},
                {"event": "done", "content": "GIL"},
            ])

            events = [
                e async for e in run_workflow_stream("解释 GIL", [], "rag")
            ]

            mock_retrieve.assert_called_once()
            status_events = [e for e in events if e["event"] == "status"]
            assert any("检索" in e["content"] for e in status_events)

    async def test_stream_dynamic_yields_steps_plan(self):
        """动态工作流流式：产生规划步骤事件"""
        with (
            patch("app.agent.workflow_executor.plan_steps_async") as mock_plan,
            patch("app.agent.workflow_executor.execute_tool") as mock_tool,
            patch("app.agent.workflow_executor.stream_chat_llm") as mock_stream,
        ):
            mock_plan.return_value = [
                {"type": "tool", "tool": "now", "args": {}},
                {"type": "llm"},
            ]
            mock_tool.return_value = {"datetime": "2025-01-01"}
            mock_stream.return_value = aiter_from_list([
                {"event": "token", "content": "现在"},
                {"event": "done", "content": "现在"},
            ])

            events = [
                e async for e in run_workflow_stream("现在几点", [], "dynamic")
            ]

            event_types = [e["event"] for e in events]
            assert "steps" in event_types
            assert "final" in event_types

    async def test_stream_error_in_llm_yields_error_event(self):
        """流式 LLM 返回 error 事件时被正确转发"""
        with patch("app.agent.workflow_executor.stream_chat_llm") as mock_stream:
            mock_stream.return_value = aiter_from_list([
                {"event": "error", "content": "API 调用失败"},
            ])

            events = [
                e async for e in run_workflow_stream("你好", [], "chat")
            ]

            error_events = [e for e in events if e["event"] == "error"]
            assert len(error_events) >= 1

    async def test_stream_dynamic_with_tool_and_rag_concurrent(self):
        """动态工作流：tool 和 rag 并发执行，都完成后调 LLM"""
        with (
            patch("app.agent.workflow_executor.plan_steps_async") as mock_plan,
            patch("app.agent.workflow_executor.execute_tool") as mock_tool,
            patch("app.agent.workflow_executor.retrieve") as mock_retrieve,
            patch("app.agent.workflow_executor.stream_chat_llm") as mock_stream,
        ):
            mock_plan.return_value = [
                {"type": "tool", "tool": "weather", "args": {"city": "厦门"}},
                {"type": "rag", "query": "厦门气候"},
                {"type": "llm"},
            ]
            mock_tool.return_value = {"temp": "25°C"}
            mock_retrieve.return_value = [{"content": "厦门气候温暖"}]
            mock_stream.return_value = aiter_from_list([
                {"event": "token", "content": "厦门今天"},
                {"event": "done", "content": "厦门今天25°C，气候温暖"},
            ])

            events = [
                e async for e in run_workflow_stream("厦门天气怎么样", [], "dynamic")
            ]

            mock_tool.assert_called_once()
            mock_retrieve.assert_called_once()
            final_events = [e for e in events if e["event"] == "final"]
            assert len(final_events) == 1


def aiter_from_list(items):
    """辅助：把 list 转为 async generator"""
    async def _gen():
        for item in items:
            yield item
    return _gen()
