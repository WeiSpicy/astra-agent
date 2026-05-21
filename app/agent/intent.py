from app.llm.intent_llm import ainvoke_intent_llm
from app.utils.logger import setup_logger

logger = setup_logger("intent")

async def detect_intent(text: str) -> str:
    prompt = f"""
    你是一个精准的AI Agent意图路由器。
    根据用户输入, 从以下4个标签中**只输出一个**: 

    - dynamic : 用户一句话包含多个不同动作或请求
    - tool    : 单一命令式工具调用（计算、查时间、执行具体工具等）
    - rag     : 询问知识、解释、原理、定义、技术概念
    - chat    : 普通对话、闲聊、问候、情绪表达或其他

    判断优先级（严格遵守）: 
    1. 如果一句话包含两个及以上不同动作 → dynamic(最高优先级）
    2. 单一明确工具调用 → tool
    3. 询问知识/原理/解释 → rag
    4. 其他全部归为 chat

    用户输入: {text}

    只输出一个单词: dynamic / tool / rag / chat,不要输出任何其他内容。
    """
    
    result = await ainvoke_intent_llm(prompt)
    intent_name = result.lower()
    logger.info(f"input={text} -> Selected Workflow={intent_name}")
    return intent_name
