import asyncio
from datetime import datetime
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agent.core import AgentCore
from app.model.chat import ChatRequest
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("chat")

agent = AgentCore()

###########################
# 基于langchain的非流式对话
###########################
@router.post("")
async def chat_endpoint(req: ChatRequest):

    result = await agent.run(req.question)
    return result

#######################
# SSE 流式对话
#######################

@router.post("/stream")
async def chat_stream(req: ChatRequest):

    async def event_generator():
        async for event in agent.stream(req.question):
            # SSE 标准格式
            yield (
                f"event: {event['event']}\n"
                f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            )

            # 让事件循环及时 flush
            await asyncio.sleep(0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 禁止缓冲
        } 
    )