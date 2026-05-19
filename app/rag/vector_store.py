import os
import threading
from typing import List, Dict

from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

from app.rag.config import VECTOR_STORE_DIR
from app.utils.logger import setup_logger

logger = setup_logger("Rag vector_store")

class VectorStoreManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(VectorStoreManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        logger.info("初始化 VectorStoreManager 单例...")
        self.embeddings = FastEmbedEmbeddings(
            model_name="BAAI/bge-small-zh-v1.5",
            cache_dir="./models",
        )
        self._vectorstore = self._load_vectorstore()

    def _load_vectorstore(self) -> FAISS | None:
        if not (os.path.exists(os.path.join(VECTOR_STORE_DIR, "index.faiss")) and 
                os.path.exists(os.path.join(VECTOR_STORE_DIR, "index.pkl"))):
            return None
        return FAISS.load_local(VECTOR_STORE_DIR, self.embeddings, allow_dangerous_deserialization=True)

    def get_vectorstore(self):
        if self._vectorstore is None:
            with self._lock:
                if self._vectorstore is None:
                    self._vectorstore = self._load_vectorstore()
        return self._vectorstore

    def add_documents(self, docs: List[Dict], progress_callback=None, batch_size: int = 256, is_rebuild: bool = False):
        """
        统一的文档写入方法。
        :param is_rebuild: 如果为 True, 则清空当前库, 重新全量构建；为 False 则代表增量追加。
        """
        # 如果文档为空则初始化一个默认空库
        if not docs:
            logger.warning("没有找到任何文档，将创建一个默认空向量库")
            vectorstore = FAISS.from_texts(
                texts=["这是一个默认的空知识库。目前还没有上传任何文档。"],
                embedding=self.embeddings,
                metadatas=[{"source": "default_empty", "path": "empty", "chunk_id": 0}],
            )
            vectorstore.save_local(VECTOR_STORE_DIR)
            self._vectorstore = vectorstore
            if progress_callback: progress_callback(100)
            return vectorstore

        if progress_callback: progress_callback(10)

        # 统一准备数据并进行批量向量化
        texts = [doc["content"] for doc in docs]
        metadatas = [{"source": doc["source"], "path": doc["path"], "chunk_id": doc["chunk_id"]} for doc in docs]
        
        vectors = self.embeddings.embed_documents(texts)
        text_embeddings = list(zip(texts, vectors))
        total = len(texts)

        # 决定是增量还是全量重构
        vectorstore = None if is_rebuild else self.get_vectorstore()

        # 分批写入内存
        for i in range(0, total, batch_size):
            end_idx = min(i + batch_size, total)
            batch_data = text_embeddings[i:end_idx]
            batch_metas = metadatas[i:end_idx]

            if vectorstore is None:
                vectorstore = FAISS.from_embeddings(batch_data, self.embeddings, batch_metas)
            else:
                vectorstore.add_embeddings(batch_data, batch_metas)

            if progress_callback:
                p = 10 + int((end_idx / total) * 90)
                progress_callback(p)

        # 统一持久化与更新状态
        vectorstore.save_local(VECTOR_STORE_DIR)
        self._vectorstore = vectorstore
        return vectorstore

    def search_docs(self, query: str, top_k: int = 3):
        vectorstore = self.get_vectorstore()
        if vectorstore is None:
            logger.error("请检查向量数据库是否正常构建")
            return []
        return vectorstore.similarity_search(query=query, k=top_k)

vector_manager = VectorStoreManager()