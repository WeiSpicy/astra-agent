import re
from app.utils.logger import setup_logger

logger = setup_logger("calc")

def calc(expression: str):
    if not re.match(r'^[0-9+\-*/(). ]+$', expression):
        return "表达式不合法，只能包含数字和 +-*/()."

    try:
        result = eval(expression)
        logger.info(f"计算结果: {result}")
        return str(result)
    except Exception:
        return "计算失败，请检查表达式格式。"
