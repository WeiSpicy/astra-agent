# app/models/sse.py （建议新建这个文件）
from pydantic import BaseModel
from typing import Any, Dict, Optional
from datetime import datetime


class SSEEvent(BaseModel):
    """统一 SSE 事件模型"""
    event: str                    # 事件类型：status / tool_start / tool_result / rag_start / llm_start / final / error
    content: Optional[str] = None # 主要显示给用户的文字
    data: Optional[Dict[str, Any]] = None   # 额外数据（灵活）
    timestamp: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# 可选：为常用事件定义子类（更严格约束）
class StatusEvent(SSEEvent):
    event: str = "status"

class ToolStartEvent(SSEEvent):
    event: str = "tool_start"
    data: Dict[str, Any]   # 必须包含 tool 字段