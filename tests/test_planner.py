from unittest.mock import patch
from app.agent.planner import plan_steps_async


class TestPlannerFallback:
    async def test_llm_returns_garbage_triggers_fallback(self):
        """LLM 返回无法解析的内容时，降级为默认 llm 步骤"""
        with patch("app.agent.planner.ainvoke_intent_llm") as mock_llm:
            mock_llm.return_value = "乱七八糟不是json"

            steps = await plan_steps_async("你好")

            assert steps == [
                {"type": "llm", "prompt": "直接回答用户问题: 你好"}
            ]

    async def test_llm_returns_valid_json(self):
        """LLM 返回合法 JSON 时正确解析"""
        with patch("app.agent.planner.ainvoke_intent_llm") as mock_llm:
            mock_llm.return_value = (
                '[{"type": "tool", "tool": "calc", "args": {"expression": "1+2"}},'
                '{"type": "llm"}]'
            )

            steps = await plan_steps_async("1+2等于多少")

            assert len(steps) == 2
            assert steps[0] == {"type": "tool", "tool": "calc", "args": {"expression": "1+2"}}
            assert steps[1] == {"type": "llm"}

    async def test_llm_raises_exception_triggers_fallback(self):
        """LLM 调用异常时，降级为默认 llm 步骤"""
        with patch("app.agent.planner.ainvoke_intent_llm") as mock_llm:
            mock_llm.side_effect = Exception("连接超时")

            steps = await plan_steps_async("帮我查天气")

            assert steps[0]["type"] == "llm"
            assert "直接回答" in steps[0]["prompt"]
