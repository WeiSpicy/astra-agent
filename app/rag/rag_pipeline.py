from app.rag.loader import load_docs_from_dir
from app.rag.vector_store import (
    build_vectorstore,
    load_vectorstore,
    search_docs,
)

from app.utils.logger import setup_logger
from app.llm.llm_client import chat_llm


logger = setup_logger("RAG Pipeline")


# -----------------------------------
# 初始化向量库
# 不存在则自动构建
# -----------------------------------

def init_vectorstore(doc_dir="docs"):

    vectorstore = load_vectorstore()

    if vectorstore is not None:
        logger.info("已加载本地向量库")
        return vectorstore

    logger.info("本地向量库不存在，开始构建...")

    docs = load_docs_from_dir(doc_dir)

    vectorstore = build_vectorstore(docs)

    logger.info("向量库构建完成")

    return vectorstore


# -----------------------------------
# RAG Retrieval
# -----------------------------------

def retrieve(question: str, top_k: int = 3):

    results = search_docs(
        query=question,
        top_k=top_k,
    )

    return results


# -----------------------------------
# RAG Answer
# -----------------------------------

def rag_answer(question: str):

    docs = retrieve(question, top_k=3)

    if not docs:
        return {
            "answer": "知识库中未找到相关内容",
            "sources": [],
        }

    context = "\n\n".join([
        f"[{doc.metadata.get('source')}]\n{doc.page_content}"
        for doc in docs
    ])

    prompt = f"""
    你是一个基于知识库进行回答的 AI 助手。

    以下是从知识库中检索到的内容：

    {context}

    请基于知识库内容回答问题。

    要求：
    1. 优先依据知识库内容回答
    2. 如果知识库中没有答案，请明确说明
    3. 不要编造不存在的信息

    用户问题：
    {question}
    """

    response = chat_llm.invoke(prompt)

    return {
        "answer": response.content,
        "sources": [
            doc.metadata.get("source")
            for doc in docs
        ],
    }