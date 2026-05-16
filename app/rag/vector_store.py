import os
from typing import List, Dict

from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

from app.rag.config import VECTOR_STORE_DIR

# 职责: 基于基于 LangChain FAISS 实现 embedding + FAISS persistence +retrieval

# -----------------------------------
# Embedding Model
# -----------------------------------

embeddings = FastEmbedEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir="./models",
)


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


# -----------------------------------
# 加载向量库
# -----------------------------------

def load_vectorstore() -> FAISS | None:

    if not os.path.exists(VECTOR_STORE_DIR):
        return None

    return FAISS.load_local(
        VECTOR_STORE_DIR,
        embeddings,
        allow_dangerous_deserialization=True,
    )


# -----------------------------------
# 检索
# -----------------------------------

def search_docs(query: str, top_k: int = 3):

    vectorstore = load_vectorstore()

    if vectorstore is None:
        return []

    results = vectorstore.similarity_search(
        query=query,
        k=top_k,
    )

    return results