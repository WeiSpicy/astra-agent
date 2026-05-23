from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime, timezone


class SSEEvent(BaseModel):
    event: str
    content: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )