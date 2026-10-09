# 由于静态工作流太蠢了, 所以转向动态工作流的怀抱
# 让 LLM 生成步骤列表

import json
from app.llm.intent_llm import ainvoke_intent_llm
from app.utils.logger import setup_logger

logger = setup_logger("Planner")

async def plan_steps_async(user_input: str):
    prompt = f"""[Task]
        Analyze user input and output a strict JSON array of execution steps. Do NOT include markdown tags or trailing text.

        [Hard Rules]
        1. Output MUST contain at least 1 step. Empty array [] is FORBIDDEN.
        2. The LAST step MUST be {{"type": "llm"}}. No exceptions — even if the plan only has one step.
        3. If the user does not specify a city, the 'city' parameter MUST default to '厦门'.
        4. Strictly FORBIDDEN to use placeholders like 'current_city', or 'unknown'.
        5. Greeting, casual chat, or unrecognizable input → output [{{"type": "llm"}}].

        [Available Tools]
        - calc: {{"expression": "math expression"}}
        - now: No args
        - weather: {{"city": "city name"}}

        [Step Types]
        - tool: For calculation, date/time, or weather.
        - rag: For concepts, definitions, principles. Requires: {{"query": "search query"}}
        - llm: Final summary. MUST be present and MUST be the last step. Strictly ONLY {{"type": "llm"}} without other keys.

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

        content = result.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].removesuffix("```").strip()

        steps = json.loads(content)

        for step in steps:
            step["type"] = step["type"].lower()
            if "tool" in step:
                step["tool"] = step["tool"].lower()
            
        logger.debug(f"成功生成步骤: {steps}")
        return steps
        
    except Exception as e:
        logger.error(f"生成失败: {e}\n输出内容: {repr(result) if 'result' in locals() else 'None'}")
        # 降级处理
        return [
            {"type": "llm"}
        ]
