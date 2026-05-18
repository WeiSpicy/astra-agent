# app/models/sse.py （建议新建这个文件）
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class SSEEvent(BaseModel):
    """统一 SSE 事件模型"""
    event: str                    # 事件类型：status / tool_start / tool_result / rag_start / llm_start / final / error
    content: Optional[str] = None # 主要显示给用户的文字
    data: Optional[Dict[str, Any]] = None   # 额外数据（灵活）
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )