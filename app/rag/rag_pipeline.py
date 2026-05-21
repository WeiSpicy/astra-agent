from app.rag.loader import load_docs_from_dir
from app.rag.vector_store import vector_manager
from app.utils.logger import setup_logger
from app.llm.llm_client import chat_llm
from app.config import KNOWLEDGE_DIR

logger = setup_logger("RAG Pipeline")

def init_vectorstore(knowledge_dir=KNOWLEDGE_DIR):
    """初始化向量库 (FastAPI lifespan 调用)"""
    
    # 检查单例是否已经成功从磁盘加载了现有向量库
    if vector_manager.get_vectorstore() is not None:
        logger.info("已加载本地已有向量库")
        return

    logger.info("本地向量库不存在，开始从本地目录扫描构建...")
    docs = load_docs_from_dir(knowledge_dir)
    
    # 统一直接调用单例的 add_documents 接口完成首次全量构建
    vector_manager.add_documents(docs)
    logger.info("本地向量库冷启动全量构建完成")

# -----------------------------------
# RAG Retrieval & Answer
# -----------------------------------
def retrieve(question: str, top_k: int = 3):
    logger.info("正在进行 RAG 检索")
    results = vector_manager.search_docs(
        query=question,
        top_k=top_k,
    )

    return results

def rag_answer(question: str):
    # 直接调用单例自带的检索方法
    docs = vector_manager.search_docs(query=question, top_k=3)

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
        "sources": list(set([doc.metadata.get("source") for doc in docs])),
    }