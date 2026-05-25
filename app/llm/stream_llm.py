# app/llm/stream_llm.py

from openai import AsyncOpenAI

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL
from app.model.sse import SSEEvent
from app.utils.logger import setup_logger

logger = setup_logger("stream_llm")

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

SYSTEM_PROMPT = """
你是一个专业的 AI 助手。

规则：
1. 如果提供了 context_docs, 请优先基于知识库回答
2. 如果提供了 tool_result, 请结合工具结果回答, 你有可能获得多工具执行结果, 请不要遗漏
3. 如果知识库没有相关信息，请明确说明
4. 不要编造不存在的信息
"""


async def stream_chat_llm(
    user_input: str,
    history=None,
    context_docs=None,
    tool_result=None,
):

    history = history or []

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    for h in history:
        messages.append(
            {
                "role": h["role"],
                "content": h["content"],
            }
        )

    # 用户输入
    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    if context_docs:
        messages.append({"role": "system", "content": f"相关文档：{context_docs}"})

    if tool_result:
        messages.append({"role": "system", "content": f"工具结果：{tool_result}"})

    try:

        response = await client.chat.completions.create(
            model="deepseek-v4-pro",
            messages=messages,
            stream=True,
            reasoning_effort="high",
            extra_body={"thinking": {"type": "enabled"}},
        )

        full_content = ""

        async for chunk in response:

            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            if not delta:
                continue

            content = delta.content

            if not content:
                continue

            full_content += content

            yield SSEEvent(
                event="token",
                content=content,
            ).model_dump()

        yield SSEEvent(
            event="done",
            content=full_content,
        ).model_dump()

    except Exception as e:

        logger.exception("流式 LLM 调用失败")

        yield SSEEvent(
            event="error",
            content=str(e),
        ).model_dump()
