from fastapi import APIRouter, HTTPException
from app.model.rag import RAGQueryRequest, RagResponse
from app.rag.rag_pipeline import retrieve, rag_answer
from app.rag.vector_store import vector_manager
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
    
    
@router.get("/debug/vectorstore")
async def debug_vectorstore(limit: int = 20):
    """
    查看当前向量库中的 chunk 数据
    """

    try:

        vectorstore = vector_manager.get_vectorstore()

        if vectorstore is None:
            return {
                "loaded": False,
                "message": "向量库未加载"
            }

        # LangChain FAISS 内部 docstore
        docs = vectorstore.docstore._dict

        results = []

        for i, (doc_id, doc) in enumerate(docs.items()):

            if i >= limit:
                break

            results.append({
                "doc_id": doc_id,
                "content_preview": (
                    doc.page_content[:200] + "..."
                    if len(doc.page_content) > 200
                    else doc.page_content
                ),
                "metadata": doc.metadata,
            })

        return {
            "loaded": True,
            "total_chunks": len(docs),
            "showing": len(results),
            "chunks": results,
        }

    except Exception as e:
        logger.exception("查看向量库失败")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )