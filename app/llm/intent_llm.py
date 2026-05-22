# app/llm/intent_llm.py
from openai import AsyncOpenAI

from app.config import DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY
from app.utils import setup_logger

logger = setup_logger("LLM intent")

aclient = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

async def ainvoke_intent_llm(prompt: str):
    """
    异步调用 LLM 进行意图识别
    """
    response = await aclient.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[{"role": "user", "content": prompt}],
        stream=False,
        extra_body={"thinking": {"type": "disabled"}}
    )
    
    return response.choices[0].message.content.strip()