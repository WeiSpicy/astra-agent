import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
# 引入基于 ONNX Runtime 的轻量级 Embedding 库
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

_vectorstore = None

# 查看模型
# print(TextEmbedding.list_supported_models())
# 依然是 bge-small-zh，但底层是 ONNX Runtime，这里为了减小项目体积，毕竟只是demo
embeddings = FastEmbedEmbeddings(
    model_name="BAAI/bge-small-zh-v1.5",
    cache_dir="./models"  # 模型会自动下载并解压到你项目根目录的 models/ 文件夹中
)

def load_vectorstore():
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    doc_path = "docs/intro.md"
    if not os.path.exists(doc_path):
        os.makedirs(os.path.dirname(doc_path), exist_ok=True)
        with open(doc_path, "w", encoding="utf-8") as f:
            f.write("# FastAPI 简介\nFastAPI 是一个现代、快速（高性能）的 Web 框架，用于构建 API。它基于 Python 3.7+ 和标准类型提示。")

    loader = TextLoader(doc_path, encoding="utf-8")
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    _vectorstore = FAISS.from_documents(chunks, embeddings)
    return _vectorstore

def rag_query(query: str):
    vectorstore = load_vectorstore()
    results = vectorstore.similarity_search(query, k=2)
    return [r.page_content for r in results]