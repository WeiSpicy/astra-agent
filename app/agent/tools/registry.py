# 工具注册列表
from app.agent.tools.builtin.calc import calc
from app.agent.tools.builtin.now import now
from app.agent.tools.builtin.weather import weather

TOOLS = {
    "calc": {
        "fn": calc,
        "description": "简单数学计算"
    },
    "now": {
        "fn": now,
        "description": "获取当前时间"
    },
    "weather": {
        "fn": weather,
        "description": "使用 和风天气API 查询某个城市的天气"
    }
}
