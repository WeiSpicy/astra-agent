import json
from app.agent.tools.registry import TOOLS
from app.utils.logger import setup_logger

logger = setup_logger("tools")


def execute_tool(tool_name: str, args: dict):
    logger.info(f"工具调用: {json.dumps({'tool': tool_name, 'args': args}, ensure_ascii=False)}")

    if tool_name not in TOOLS:
        return f"未知工具: {tool_name}"

    tool_fn = TOOLS[tool_name]["fn"]

    try:
        return tool_fn(**args)
    except TypeError as e:
        return f"工具参数错误: {str(e)}"
    except Exception as e:
        return f"工具执行失败: {str(e)}"
