# app/agent/tools.py

from datetime import datetime
import json
import re

from app.llm.tool_llm import parse_tool_call
from app.utils.logger import setup_logger

logger = setup_logger("tools")

def calc(expression: str):
    """简单计算器，只允许 +-*/() 和数字"""
    try:
        # 安全检查：只允许数字和 +-*/().
        if not re.match(r'^[0-9+\-*/(). ]+$', expression):
            return "表达式不合法，只能包含数字和 +-*/()."

        result = eval(expression)
        logger.info(f"调用 clc 工具, 结果: {result}")
        return str(result)
    except Exception:
        return "计算失败，请检查表达式格式。"

def now():
    """返回当前日期、时间、星期几"""
    dt = datetime.now()
    return {
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": dt.strftime("%A"),
        "time": dt.strftime("%H:%M:%S")
    }

# 工具注册表
TOOLS = {
    "calc": calc,
    "now": now
}


def run_tool(user_input: str):
    # 让 LLM 解析工具调用
    parsed = parse_tool_call(user_input)
    logger.info(f"工具意图识别: {parsed}")
    try:
        data = json.loads(parsed)
    except Exception:
        return f"工具调用解析失败：{parsed}"

    tool_name = data.get("tool")
    args = data.get("args", {})

    if tool_name not in TOOLS:
        return f"未知工具：{tool_name}"

    tool_fn = TOOLS[tool_name]
    return tool_fn(**args)
