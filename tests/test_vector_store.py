import threading
import time
from unittest.mock import patch, MagicMock

from app.rag.vector_store import vector_manager


class TestAddDocumentsLock:
    """add_documents 写锁验证：不执行真实 FAISS 写入，仅验证锁的互斥行为"""

    def test_write_lock_acquired_during_add(self):
        """add_documents() 进入时获取 _write_lock，退出时释放"""
        with patch.object(vector_manager, "_write_lock") as mock_lock:
            vector_manager.add_documents([])

            mock_lock.__enter__.assert_called_once()
            mock_lock.__exit__.assert_called_once()

    def test_write_lock_serializes_concurrent_writes(self):
        """两个线程同时抢 _write_lock，后到的必须等先到的释放"""
        results = []
        t1_entered = threading.Event()

        def writer(label: str, entered: threading.Event):
            with vector_manager._write_lock:
                results.append(f"{label}_enter")
                entered.set()
                time.sleep(0.3)
                results.append(f"{label}_exit")

        t1 = threading.Thread(target=writer, args=("t1", t1_entered))
        t2 = threading.Thread(target=writer, args=("t2", threading.Event()))

        t1.start()
        assert t1_entered.wait(timeout=2), "t1 未能在 2s 内获取锁"
        t2.start()
        t1.join(timeout=5)
        t2.join(timeout=5)

        assert results == ["t1_enter", "t1_exit", "t2_enter", "t2_exit"], (
            f"锁未正确串行化，实际顺序: {results}"
        )

    def test_write_lock_covers_non_empty_docs_path(self):
        """非空文档路径也持有 _write_lock，覆盖 embedding → add_embeddings → save_local"""
        fake_docs = [{"content": "测试文档", "source": "test.txt", "path": "test.txt", "chunk_id": 0}]

        with patch.object(vector_manager, "_write_lock") as mock_lock:
            with patch.object(vector_manager.embeddings, "embed_documents") as mock_embed:
                mock_embed.return_value = [[0.1] * 512]
                with patch.object(vector_manager, "get_vectorstore") as mock_get_vs:
                    mock_vs = MagicMock()
                    mock_get_vs.return_value = mock_vs

                    vector_manager.add_documents(fake_docs)

            mock_lock.__enter__.assert_called_once()
            mock_lock.__exit__.assert_called_once()
            mock_embed.assert_called_once()
            mock_vs.add_embeddings.assert_called()
            mock_vs.save_local.assert_called_once()
