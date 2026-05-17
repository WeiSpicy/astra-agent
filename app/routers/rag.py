from fastapi import APIRouter, HTTPException
from app.model.rag import RAGQueryRequest, RagResponse
from app.rag.rag_pipeline import retrieve, rag_answer
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger("rag")

@router.post("/query", response_model=RagResponse)
async def rag_query(request: RAGQueryRequest):
    """RAG 知识检索 + 生成回答"""
    try:
        # 使用完整的 rag_answer（带LLM生成）
        result = rag_answer(request.query)

        return RagResponse(
            query=request.query,
            answer=result["answer"],
            sources=result.get("sources", []),
            raw_docs=None  # 如果需要调试可以返回
        )

    except Exception as e:
        logger.exception("RAG 查询失败")
        raise HTTPException(status_code=500, detail=f"RAG 查询失败: {str(e)}")


@router.post("/retrieve")
async def rag_retrieve(request: RAGQueryRequest):
    """仅检索文档, 用于调试"""
    try:
        docs = retrieve(request.query, top_k=request.top_k)
        
        return {
            "query": request.query,
            "docs": [
                {
                    "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                    "source": doc.metadata.get("source"),
                    "score": getattr(doc, "score", None)
                }
                for doc in docs
            ]
        }
    except Exception as e:
        logger.exception("RAG 检索失败")
        raise HTTPException(status_code=500, detail=str(e))