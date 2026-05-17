from fastapi import APIRouter
from app.utils.logger import setup_logger
from app.agent.core import AgentCore
from app.model.chat import ChatRequest

router = APIRouter()
logger = setup_logger("ask")

agent = AgentCore()

@router.post("")
async def chat_endpoint(req: ChatRequest):
    result = await agent.run(req.question)
    return result