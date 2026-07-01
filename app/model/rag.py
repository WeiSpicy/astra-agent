from typing import List, Optional

from pydantic import BaseModel, Field

class RAGQueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = Field(default=3, gt=0)
    
class RagResponse(BaseModel):
    query: str
    answer: str
    sources: List[str] = []
    raw_docs: Optional[List[dict]] = None # 调试时可返回原始文档