from unittest.mock import patch, MagicMock

from app.rag.rag_pipeline import rag_answer, retrieve


class TestRagAnswer:
    """rag_answer 单元测试：验证 top_k 参数正确传递给 search_docs"""

    def test_default_top_k_is_3(self):
        """不传 top_k 时默认查询 3 条文档"""
        with patch("app.rag.rag_pipeline.vector_manager.search_docs") as mock_search:
            mock_search.return_value = [
                MagicMock(page_content="doc1", metadata={"source": "a.txt"}),
                MagicMock(page_content="doc2", metadata={"source": "b.txt"}),
                MagicMock(page_content="doc3", metadata={"source": "c.txt"}),
            ]
            with patch("app.rag.rag_pipeline.chat_llm") as mock_llm:
                mock_llm.invoke.return_value = MagicMock(content="回答")

                rag_answer("测试问题")

                mock_search.assert_called_once_with(query="测试问题", top_k=3)

    def test_top_k_forwarded_to_search_docs(self):
        """传入 top_k=5 时 search_docs 收到 k=5"""
        with patch("app.rag.rag_pipeline.vector_manager.search_docs") as mock_search:
            mock_search.return_value = [
                MagicMock(page_content=f"doc{i}", metadata={"source": f"f{i}.txt"})
                for i in range(5)
            ]
            with patch("app.rag.rag_pipeline.chat_llm") as mock_llm:
                mock_llm.invoke.return_value = MagicMock(content="回答")

                rag_answer("测试问题", top_k=5)

                mock_search.assert_called_once_with(query="测试问题", top_k=5)

    def test_top_k_1_returns_one_source(self):
        """top_k=1 时只返回 1 条来源"""
        with patch("app.rag.rag_pipeline.vector_manager.search_docs") as mock_search:
            mock_search.return_value = [
                MagicMock(page_content="only doc", metadata={"source": "single.txt"}),
            ]
            with patch("app.rag.rag_pipeline.chat_llm") as mock_llm:
                mock_llm.invoke.return_value = MagicMock(content="简短回答")

                result = rag_answer("问题", top_k=1)

                assert len(result["sources"]) == 1
                assert result["sources"][0] == "single.txt"

    def test_no_docs_returns_fallback(self):
        """知识库无结果时返回兜底回答"""
        with patch("app.rag.rag_pipeline.vector_manager.search_docs") as mock_search:
            mock_search.return_value = []

            result = rag_answer("无匹配问题")

            assert result["answer"] == "知识库中未找到相关内容"
            assert result["sources"] == []

    def test_top_k_none_falls_back_to_default(self):
        """top_k=None 时回退到默认值 3"""
        with patch("app.rag.rag_pipeline.vector_manager.search_docs") as mock_search:
            mock_search.return_value = []
            with patch("app.rag.rag_pipeline.chat_llm") as mock_llm:
                mock_llm.invoke.return_value = MagicMock(content="回答")

                rag_answer("问题", top_k=None)

                # None 透传到了 search_docs，由它内部兜底为 3
                mock_search.assert_called_once_with(query="问题", top_k=None)

    def test_top_k_zero_falls_back_to_default(self):
        """top_k=0 时回退到默认值 3"""
        with patch("app.rag.rag_pipeline.vector_manager.search_docs") as mock_search:
            mock_search.return_value = []
            with patch("app.rag.rag_pipeline.chat_llm") as mock_llm:
                mock_llm.invoke.return_value = MagicMock(content="回答")

                rag_answer("问题", top_k=0)

                mock_search.assert_called_once_with(query="问题", top_k=0)


class TestRetrieve:
    """retrieve 函数：确认已有的 top_k 转发不受影响"""

    def test_retrieve_forwards_top_k(self):
        with patch("app.rag.rag_pipeline.vector_manager.search_docs") as mock_search:
            mock_search.return_value = []

            retrieve("查询", top_k=7)

            mock_search.assert_called_once_with(query="查询", top_k=7)
