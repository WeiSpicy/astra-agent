# app/agent/memory.py

from app.config import MAX_HISTORY
from collections import deque

# 保存最近 5 轮对话
conversation_history = deque(maxlen=MAX_HISTORY)

def add_message(role: str, content: str):
    conversation_history.append({"role": role, "content": content})

def get_history():
    return list(conversation_history)
