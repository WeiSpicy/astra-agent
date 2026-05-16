# 由于静态工作流太蠢了, 所以转向动态工作流的怀抱
# 让 LLM 生成步骤列表

import json
from app.llm.llm_client import chat_llm
from app.utils.logger import setup_logger

logger = setup_logger("Planner")

def plan_steps(user_input: str):
    prompt = f"""你是一个严格的AI Agent Planner。
    用户输入: {user_input}

    可用工具: calc(计算器), now(当前时间)

    可用步骤类型:
    - tool: 调用工具(calc, now)
    - rag : 知识检索(询问概念、原理、定义、技术框架、如何使用等)
    - llm : 最终总结或普通对话

    判断规则(严格遵守优先级):
    1. 如果包含计算、时间等明确工具动作 → 优先 tool
    2. 如果用户在**询问知识、概念、原理、定义、技术框架**(如 FastAPI是什么、Redis为什么快、GIL是什么)→ 必须使用 rag
    3. 如果有多个动作 → 拆分成多个步骤
    4. 最后一般需要一个 llm 步骤做友好总结

    输出严格JSON数组, 不要任何其他文字:

    示例:
    [
    {{"type": "tool", "tool": "calc", "args": {{"expression": "89*89"}}}},
    {{"type": "rag", "query": "FastAPI是什么"}},
    {{"type": "llm", "prompt": "用友好语气总结"}}
    ]

    """
    try:
        result = chat_llm.invoke(prompt)
        content = result.content.strip()
        
        # 清理可能的多余内容
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].strip()
            
        steps = json.loads(content)
        logger.info(f"Planner 成功生成步骤: {steps}")
        return steps
        
    except Exception as e:
        logger.error(f"Planner 生成失败: {e}\n输出内容: {result.content if 'result' in locals() else 'None'}")
        # 降级处理
        return [
            {"type": "llm", "prompt": f"直接回答用户问题: {user_input}"}
        ]
