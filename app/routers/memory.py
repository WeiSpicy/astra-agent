from fastapi import APIRouter, Query
from app.agent.memory import get_recent, conversation_history

router = APIRouter()

@router.get("/history")
def get_history(limit: int = Query(10, ge=1, le=50)):
    return {
        "count": len(conversation_history),
        "data": get_recent(limit)
    }
    
@router.delete("/history")
def clear_history():
    conversation_history.clear()
    return {"message": "history cleared"}

@router.get("/state")
def memory_state():
    return {
        "max_size": conversation_history.maxlen,
        "current_size": len(conversation_history),
    }