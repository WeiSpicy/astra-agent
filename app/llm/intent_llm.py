# app/llm/intent_llm.py
from app.config import DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY
from langchain_openai import ChatOpenAI

intent_llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model="deepseek-v4-pro",
    temperature=0,
)
