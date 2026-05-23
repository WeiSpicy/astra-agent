# 由于静态工作流太蠢了, 所以转向动态工作流的怀抱
# 让 LLM 生成步骤列表

import json
from app.llm.intent_llm import ainvoke_intent_llm
from app.utils.logger import setup_logger

logger = setup_logger("Planner")

async def plan_steps_async(user_input: str):
    prompt = f"""[Task]
        Analyze user input and output a strict JSON array of execution steps. Do NOT include markdown tags or trailing text.

        [Business Rules]
        1. Extract parameters based strictly on specific locations.
        2. If the user does not specify a city, the 'city' parameter MUST default to '厦门'.
        3. Strictly FORBIDDEN to use placeholders like 'current_city', or 'unknown'.
        4. Crucial: If the input is just a greeting or casual chat, the steps list MUST still contain at least [[{{"type": "llm"}}] so the assistant can respond.        
        
        [Available Tools]
        - calc: {{"expression": "math expression"}}
        - now: No args
        - weather: {{"city": "city name"}}

        [Step Types]
        - tool: For calculation, date/time, or weather.
        - rag: For concepts, definitions, principles. Requires: {{"query": "search query"}}
        - llm: Final summary. Must be the last step. Strictly ONLY {{"type": "llm"}} without other keys.

        [User Input]
        {user_input}

        [Output Example]
        [
            {{"type": "tool", "tool": "calc", "args": {{"expression": "89*89"}}}},
            {{"type": "tool", "tool": "weather", "args": {{"city": "厦门"}}}},
            {{"type": "rag", "query": "FastAPI"}},
            {{"type": "llm"}}
        ]"""
    try:
        result = await ainvoke_intent_llm(prompt)
        content = result.lower()
        
        # 清理可能的多余内容
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].strip()
             
        steps = json.loads(content)
            
        logger.info(f"成功生成步骤: {steps}")
        return steps
        
    except Exception as e:
        logger.error(f"生成失败: {e}\n输出内容: {repr(result) if 'result' in locals() else 'None'}")
        # 降级处理
        return [
            {"type": "llm", "prompt": f"直接回答用户问题: {user_input}"}
        ]
