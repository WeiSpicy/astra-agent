import asyncio
import json

from fastapi import APIRouter
from app.utils.logger import setup_logger
from app.agent.core import AgentCore
from app.model.chat import ChatRequest
# from sse_starlette.sse import EventSourceResponse
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = setup_logger("ask")

agent = AgentCore()

@router.post("")
async def chat_endpoint(req: ChatRequest):
    result = await agent.run(req.question)
    return result

#######################
# 对话过程流式传输
#######################

@router.post("/stream")
async def chat_stream(req: ChatRequest):

    async def event_generator():
        async for event in agent.stream(req.question):
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )