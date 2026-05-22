from fastapi import APIRouter, Query
from app.agent.memory import clear_all_histories, get_recent, get_history, clear_user_history
from app.config import MAX_HISTORY

router = APIRouter()

# =========================
# 获取历史记录
# =========================
@router.get("/history")
def get_chat_history(
    limit: int = Query(10, ge=1, le=50),
    session_id: str = "default_session"
):
    """
    获取指定 session 的历史记录。
    """
    current_room_history = get_history(session_id=session_id)
    
    return {
        "count": len(current_room_history),
        "data": get_recent(limit=limit, session_id=session_id)
    }

# =========================
# 清空历史记录
# =========================
@router.delete("/history")
def clear_history(
    session_id: str = "default_session"
):
    clear_user_history(session_id=session_id)
    return {"message": f"history for session '{session_id}' cleared"}

@router.delete("/history/all")
def clear_all_users_history():

    clear_all_histories()
    return {"message": "All session histories in memory have been cleared globally."}

# =========================
# 监控内存状态
# =========================
@router.get("/state")
def memory_state(
    session_id: str = "default_session"
):
    current_room_history = get_history(session_id=session_id)
        
    return {
        "max_size": MAX_HISTORY,
        "current_size": len(current_room_history),
        "session_id": session_id
    }