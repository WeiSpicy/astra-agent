from app.agent.tools.base import execute_tool


class TestExecuteTool:
    def test_calc_via_execute(self):
        result = execute_tool("calc", {"expression": "2 + 3"})
        assert "5" in result

    def test_now_via_execute(self):
        result = execute_tool("now", {})
        assert isinstance(result, dict)
        assert "date" in result

    def test_unknown_tool(self):
        result = execute_tool("no_such_tool", {})
        assert "未知工具" in result

    def test_wrong_args(self):
        result = execute_tool("calc", {"wrong_key": "value"})
        assert "工具参数" in result or "失败" in result
