from fastapi import APIRouter
from app.utils.logger import setup_logger
from app.agent.core import AgentCore

logger = setup_logger("ask")
router = APIRouter()
agent = AgentCore()

@router.post("")
def chat_endpoint(payload: dict):
    user_input = payload.get("question", "")
    result = agent.run(user_input)
    return result