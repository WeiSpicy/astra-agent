import os
from typing import List, Dict

from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

from app.rag.config import VECTOR_STORE_DIR
from app.utils.logger import setup_logger

# 职责: 基于基于 LangChain FAISS 实现 embedding + FAISS persistence +retrieval

# -----------------------------------
# Embedding Model
# -----------------------------------

embeddings = FastEmbedEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir="./models",
)

_VECTORSTORE = None
logger = setup_logger("Rag vector_store")

# -----------------------------------
# 构建向量库
# docs:
# [
#   {
#       "content": "...",
#       "source": "...",
#       "path": "...",
#       "chunk_id": 0,
#   }
# ]
# -----------------------------------

def build_vectorstore(docs: List[Dict]) -> FAISS:
    """构建 FAISS 向量库"""
    
    if not docs:
        logger.warning("没有找到任何文档，将创建一个默认空向量库")
        # 创建一个默认文档，避免完全空的向量库导致后续错误
        default_texts = ["这是一个默认的空知识库。目前还没有上传任何文档。请先上传文档后再进行查询。"]
        default_metadatas = [{"source": "default_empty", "path": "empty", "chunk_id": 0}]
        
        vectorstore = FAISS.from_texts(
            texts=default_texts,
            embedding=embeddings,
            metadatas=default_metadatas,
        )
        vectorstore.save_local(VECTOR_STORE_DIR)
        logger.info("已创建默认空向量库")
        return vectorstore
    
    texts = [doc["content"] for doc in docs]

    metadatas = [
        {
            "source": doc["source"],
            "path": doc["path"],
            "chunk_id": doc["chunk_id"],
        }
        for doc in docs
    ]

    vectorstore = FAISS.from_texts(
        texts=texts,
        embedding=embeddings,
        metadatas=metadatas,
    )

    # 持久化保存
    vectorstore.save_local(VECTOR_STORE_DIR)
    
    return vectorstore

def rebuild_vectorstore(docs: List[Dict]):
    global _VECTORSTORE
    _VECTORSTORE = build_vectorstore(docs)

# -----------------------------------
# 加载向量库
# -----------------------------------

def load_vectorstore() -> FAISS | None:

    if not (
        os.path.exists(os.path.join(VECTOR_STORE_DIR, "index.faiss")) and
        os.path.exists(os.path.join(VECTOR_STORE_DIR, "index.pkl"))
    ):
        return None

    return FAISS.load_local(
        VECTOR_STORE_DIR,
        embeddings,
        allow_dangerous_deserialization=True,
    )

def get_vectorstore():
    global _VECTORSTORE
    
    if _VECTORSTORE is None:
        _VECTORSTORE = load_vectorstore()
        
    return _VECTORSTORE


# -----------------------------------
# 检索
# -----------------------------------

def search_docs(query: str, top_k: int = 3):

    vectorstore = get_vectorstore()

    if vectorstore is None:
        logger.error("请检查向量数据库是否正常构建")
        return []

    results = vectorstore.similarity_search(
        query=query,
        k=top_k,
    )

    return results