import ast
import math
import operator

from app.utils.logger import setup_logger

logger = setup_logger("calc")

SAFE_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

SAFE_UNARY_OPS = {
    ast.USub: operator.neg,
}

SAFE_FUNCS = {
    "abs": abs,
    "round": round,
    "sqrt": math.sqrt,
    "sin": math.sin,
    "cos": math.cos,
    "log": math.log,
    "log10": math.log10,
}

SAFE_CONSTANTS = {
    "pi": math.pi,
    "e": math.e,
}


def _eval_node(node):
    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in SAFE_BINARY_OPS:
            raise ValueError(f"不支持的运算符: {type(node.op).__name__}")
        return SAFE_BINARY_OPS[op_type](
            _eval_node(node.left), _eval_node(node.right),
        )

    if isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in SAFE_UNARY_OPS:
            raise ValueError(f"不支持的一元运算符: {type(node.op).__name__}")
        return SAFE_UNARY_OPS[op_type](_eval_node(node.operand))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("不支持复杂的函数调用")
        name = node.func.id
        if name not in SAFE_FUNCS:
            raise ValueError(f"不支持的函数: {name}")
        args = [_eval_node(a) for a in node.args]
        return SAFE_FUNCS[name](*args)

    if isinstance(node, ast.Name):
        if node.id in SAFE_CONSTANTS:
            return SAFE_CONSTANTS[node.id]
        raise ValueError(f"不支持的变量: {node.id}")

    raise ValueError("表达式包含不支持的语法")


def calc(expression: str):
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _eval_node(tree.body)
        logger.info(f"计算: {expression} = {result}")
        return str(result)
    except SyntaxError:
        return "表达式语法错误，请检查括号是否配对。"
    except ZeroDivisionError:
        return "不能除以零。"
    except ValueError as e:
        return str(e)
    except Exception:
        logger.exception("calc 执行异常")
        return "计算失败，请检查表达式格式。"
