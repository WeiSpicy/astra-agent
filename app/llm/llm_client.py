from app.config import DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY
from app.utils.logger import setup_logger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = setup_logger("llm_client")

chat_llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model="deepseek-v4-pro",
    temperature=0,
)

SYSTEM_PROMPT = """
你是一个专业的 AI 助手。

规则：
1. 如果提供了 context_docs, 请优先基于知识库回答
2. 如果提供了 tool_result, 请结合工具结果回答
3. 如果知识库没有相关信息，请明确说明
4. 不要编造不存在的信息
"""
def chat_with_llm(user_input: str, history=None, context_docs=None, tool_result=None):
    history = history or []

    messages = []

    messages.append({
        "role": "system",
        "content": SYSTEM_PROMPT,
    })
    
    # 加入历史对话
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})

    # 当前用户输入
    messages.append({"role": "user", "content": user_input})

    # 加入 RAG 文档
    if context_docs:
        messages.append({"role": "system", "content": f"相关文档：{context_docs}"})

    # 加入工具结果
    if tool_result:
        messages.append({"role": "system", "content": f"工具结果：{tool_result}"})

    result = chat_llm.invoke(messages)
    return result.content
