from app.llm.intent_llm import intent_llm
from app.utils.logger import setup_logger

logger = setup_logger("intent")

def detect_intent(text: str) -> str:
    prompt = prompt = f"""
    你是一个意图分类器，只输出一个词：

    - 如果用户询问当前时间、日期、星期几、现在几点、今天几号等 → 输出 tool
    - 如果用户在要求计算、执行工具 → 输出 tool
    - 如果用户在问知识、解释、是什么、原理、定义 → 输出 rag
    - 其他情况 → 输出 chat

    用户输入：{text}
    只输出 rag/tool/chat
    """
    result = intent_llm.invoke(prompt)
    logger.info(f"[Intent] input={text}, intent={result.content.strip()}")

    return result.content.strip()
