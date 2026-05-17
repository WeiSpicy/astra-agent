from typing import Any, Dict, Optional

from pydantic import BaseModel

class ToolRunRequest(BaseModel):
    tool: str
    args: Optional[Dict[str, Any]] = {}