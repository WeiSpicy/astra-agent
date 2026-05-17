from datetime import datetime

def now():
    dt = datetime.now()
    return {
        "date": dt.strftime("%Y-%m-%d"),
        "weekday": dt.strftime("%A"),
        "time": dt.strftime("%H:%M:%S")
    }
