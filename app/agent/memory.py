# app/agent/memory.py

from typing import Dict
from app.config import MAX_HISTORY
from collections import deque

# 保存最近 15 轮对话（内存字典隔离）
_user_histories: Dict[str, deque] = {}

def _get_or_create_queue(session_id: str = "default_session") -> deque:
    """如果该用户的队列不存在，则初始化一个。默认为 default_session"""
    if session_id not in _user_histories:
        _user_histories[session_id] = deque(maxlen=MAX_HISTORY)
    return _user_histories[session_id]

def add_message(role: str, content: str, session_id: str = "default_session"):
    q = _get_or_create_queue(session_id)
    q.append({"role": role, "content": content})

def get_history(session_id: str = "default_session"):
    q = _get_or_create_queue(session_id)
    return list(q)

def clear_user_history(session_id: str = "default_session"):
    """清空指定会话的历史记录"""
    if session_id in _user_histories:
        _user_histories[session_id].clear()

def get_recent(limit: int = 10, session_id: str = "default_session"):
    q = _get_or_create_queue(session_id)
    return list(q)[-limit:]

def clear_all_histories():
    """清空整个服务器上所有用户的历史记录"""
    _user_histories.clear()