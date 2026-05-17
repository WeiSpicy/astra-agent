import json
from app.agent.tools.registry import TOOLS
from app.llm.tool_llm import parse_tool_call
from app.utils.logger import setup_logger

logger = setup_logger("tools")

def execute_tool(tool_name: str, args: dict):
    if tool_name not in TOOLS:
        return f"未知工具: {tool_name}"

    tool_fn = TOOLS[tool_name]["fn"]

    try:
        return tool_fn(**args)
    except TypeError as e:
        return f"工具参数错误: {str(e)}"
    except Exception as e:
        return f"工具执行失败: {str(e)}"


def run_tool(user_input: str):
    parsed = parse_tool_call(user_input)
    logger.info(f"工具意图识别: {parsed}")

    try:
        data = json.loads(parsed)
    except Exception:
        return f"工具调用解析失败：{parsed}"

    tool_name = data.get("tool")
    args = data.get("args", {})

    return execute_tool(tool_name, args)
