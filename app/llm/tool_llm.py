from app.llm.llm_client import chat_llm

def parse_tool_call(user_input: str):
    """
    让 LLM 输出一个 JSON:
    {
      "tool": "calc",
      "args": { "expression": "1+2" }
    }
    """
    prompt = f"""
    你是一个工具调用解析器。请从用户输入中提取工具名称和参数。

    工具列表：
    - 1. calc(expression): 计算数学表达式
    - 2. now(): 返回当前日期、时间、星期几

    用户输入：{user_input}

    请严格输出 JSON, 格式如下：
    {{
    "tool": "<工具名>",
    "args": {{ ... }}
    }}
    只输出 JSON, 不要解释。
    """

    result = chat_llm.invoke(prompt)
    return result.content
