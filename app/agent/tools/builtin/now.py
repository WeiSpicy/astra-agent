from datetime import datetime
from zoneinfo import ZoneInfo

CST = ZoneInfo("Asia/Shanghai")

def now():
    dt = datetime.now(CST)
    return {
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": dt.strftime("%A"),
        "time": dt.strftime("%H:%M:%S")
    }
