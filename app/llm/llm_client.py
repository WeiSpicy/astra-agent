from app.config import DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY
from app.utils.logger import setup_logger
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

logger = setup_logger("llm_client")

llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model="deepseek-v4-pro",
    temperature=0,
)

PROMPT = ChatPromptTemplate.from_messages([
    ("system", 
     "你是一个专业的 AI 助手。\n"
     "如果提供了 context_docs, 请优先基于它回答。\n"
     "如果提供了 tool_result, 请结合工具结果回答。\n"),
    ("human", "{query}")
])

def chat_with_llm(user_input: str, context_docs=None, tool_result=None):

    # 构造上下文
    context_text = ""
    if context_docs:
        context_text += "\n\n".join(context_docs)
    if tool_result:
        context_text += f"\n\n工具结果：{tool_result}"

    final_query = f"{context_text}\n\n用户问题：{user_input}"

    prompt = PROMPT.format(query=final_query)
    result = llm.invoke(prompt)
    return result.content