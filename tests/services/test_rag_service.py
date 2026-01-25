"""
Unit tests for RAG Service

Tests the vector retrieval functionality from ChromaDB.
"""

import datetime
import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from langchain_core.documents import Document

from app.services.rag_service import (
    RAGService,
    RAGServiceNotInitializedError,
    get_rag_service,
    reset_rag_service,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset RAG service singleton before each test."""
    reset_rag_service()
    yield
    reset_rag_service()


@pytest.fixture
def mock_chroma_db():
    """Mock ChromaDB instance."""
    mock_db = MagicMock()
    return mock_db


@pytest.fixture
def mock_embeddings():
    """Mock OpenAI embeddings."""
    mock_emb = MagicMock()
    return mock_emb


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        Document(
            page_content="番茄晚疫病由致病疫霉引起",
            metadata={"source": "data/knowledge/diseases/late_blight.md"},
        ),
        Document(
            page_content="番茄早疫病由链格孢菌引起",
            metadata={"source": "data/knowledge/diseases/early_blight.md"},
        ),
        Document(
            page_content="番茄灰霉病由灰葡萄孢菌引起",
            metadata={"source": "data/knowledge/diseases/gray_mold.md"},
        ),
    ]


class TestRAGServiceInit:
    """Tests for RAG service initialization."""

    def test_singleton_pattern(self):
        """Test that RAGService implements singleton pattern."""
        service1 = RAGService()
        service2 = RAGService()
        assert service1 is service2

    def test_get_rag_service_singleton(self):
        """Test that get_rag_service returns same instance."""
        service1 = get_rag_service()
        service2 = get_rag_service()
        assert service1 is service2

    @patch("app.services.rag_service.os.path.exists")
    def test_rag_service_not_initialized_error(self, mock_exists):
        """Test that error is raised when ChromaDB doesn't exist."""
        mock_exists.return_value = False

        service = RAGService()
        with pytest.raises(RAGServiceNotInitializedError) as exc_info:
            service.query("番茄晚疫病")

        assert "ChromaDB not initialized" in str(exc_info.value)
        assert "ingest_knowledge.py" in str(exc_info.value)


class TestQuery:
    """Tests for query method."""

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_success(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls, sample_documents
    ):
        """Test successful query returns relevant documents."""
        # Setup mocks
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = sample_documents[:2]
        mock_chroma_cls.return_value = mock_db

        # Execute query
        service = get_rag_service()
        results = service.query("番茄晚疫病", top_k=2)

        # Verify
        assert len(results) == 2
        assert results[0].page_content == "番茄晚疫病由致病疫霉引起"
        mock_db.similarity_search.assert_called_once_with("番茄晚疫病", k=2)

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_filter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """Test query with metadata filter."""
        # Setup mocks
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = [
            Document(
                page_content="番茄晚疫病由致病疫霉引起",
                metadata={"source": "data/knowledge/diseases/late_blight.md"},
            )
        ]
        mock_chroma_cls.return_value = mock_db

        # Execute query with filter
        service = get_rag_service()
        results = service.query(
            "番茄晚疫病",
            top_k=3,
            filter_metadata={"category": "diseases"},
        )

        # Verify
        assert len(results) == 1
        mock_db.similarity_search.assert_called_once_with(
            "番茄晚疫病",
            k=3,
            filter={"category": "diseases"},
        )

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_empty_result(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """Test query returns empty list when no matches found."""
        # Setup mocks
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        # Execute query
        service = get_rag_service()
        results = service.query("不存在的病害")

        # Verify
        assert results == []
        mock_db.similarity_search.assert_called_once()

    def test_query_empty_string_raises_error(self):
        """Test that empty query string raises ValueError."""
        service = RAGService()

        with pytest.raises(ValueError) as exc_info:
            service.query("")

        assert "cannot be empty" in str(exc_info.value)

    def test_query_whitespace_only_raises_error(self):
        """Test that whitespace-only query raises ValueError."""
        service = RAGService()

        with pytest.raises(ValueError) as exc_info:
            service.query("   ")

        assert "cannot be empty" in str(exc_info.value)

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_top_k_parameter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls, sample_documents
    ):
        """Test that top_k parameter correctly limits results."""
        # Setup mocks
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = sample_documents[:1]
        mock_chroma_cls.return_value = mock_db

        # Execute query with different top_k values
        service = get_rag_service()

        results = service.query("番茄", top_k=1)
        assert len(results) == 1
        mock_db.similarity_search.assert_called_with("番茄", k=1)

        # Reset mock
        mock_db.reset_mock()

        results = service.query("番茄", top_k=5)
        mock_db.similarity_search.assert_called_with("番茄", k=5)

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_caches_chroma_instance(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """Test that ChromaDB instance is cached after first load."""
        # Setup mocks
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        # Execute multiple queries
        service = get_rag_service()
        service.query("查询1")
        service.query("查询2")

        # Verify Chroma class is only instantiated once
        assert mock_chroma_cls.call_count == 1


class TestErrorHandling:
    """Tests for error handling."""

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_exception_is_propagated(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """Test that exceptions from ChromaDB are propagated."""
        # Setup mocks
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.side_effect = Exception("Database connection failed")
        mock_chroma_cls.return_value = mock_db

        # Execute query
        service = get_rag_service()
        with pytest.raises(Exception) as exc_info:
            service.query("番茄晚疫病")

        assert "Database connection failed" in str(exc_info.value)


class TestQueryFilterMetadata:
    """Tests for filter_metadata edge cases and JSON serialization."""

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_list_values_in_filter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试 filter_metadata 包含列表值（原问题场景）."""
        # Setup mocks
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        # Execute query with list values (previously caused TypeError)
        service = get_rag_service()
        results = service.query(
            "番茄",
            filter_metadata={"tags": ["disease", "urgent"], "category": "pests"},
        )

        # Verify the filter was correctly passed to ChromaDB
        assert results == []
        mock_db.similarity_search.assert_called_once()
        call_kwargs = mock_db.similarity_search.call_args.kwargs
        assert call_kwargs["filter"] == {"tags": ["disease", "urgent"], "category": "pests"}

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_nested_dict_filter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试 filter_metadata 包含嵌套字典."""
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        service = get_rag_service()
        results = service.query(
            "番茄",
            filter_metadata={"meta": {"severity": "high", "confidence": 0.95}},
        )

        assert results == []
        mock_db.similarity_search.assert_called_once()
        call_kwargs = mock_db.similarity_search.call_args.kwargs
        assert call_kwargs["filter"] == {"meta": {"severity": "high", "confidence": 0.95}}

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_empty_filter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试空字典 filter_metadata（空字典为假值，不传递 filter 参数）."""
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        service = get_rag_service()
        results = service.query("番茄", filter_metadata={})

        assert results == []
        mock_db.similarity_search.assert_called_once()
        # 空字典在 Python 中为假值，不会传递 filter 参数
        call_args = mock_db.similarity_search.call_args
        assert call_args.kwargs == {} or "filter" not in call_args.kwargs

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_none_values_in_filter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试 filter_metadata 包含 None 值."""
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        service = get_rag_service()
        results = service.query(
            "番茄", filter_metadata={"category": None, "severity": "high"}
        )

        assert results == []
        mock_db.similarity_search.assert_called_once()
        call_kwargs = mock_db.similarity_search.call_args.kwargs
        assert call_kwargs["filter"] == {"category": None, "severity": "high"}

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_unicode_in_filter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试 filter_metadata 包含 Unicode 字符."""
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        service = get_rag_service()
        results = service.query(
            "番茄",
            filter_metadata={
                "中文": "病害",
                "emoji": "🍅🌿",
                "混合": ["病害", "pest", "🔥"],
            },
        )

        assert results == []
        mock_db.similarity_search.assert_called_once()
        call_kwargs = mock_db.similarity_search.call_args.kwargs
        assert call_kwargs["filter"] == {
            "中文": "病害",
            "emoji": "🍅🌿",
            "混合": ["病害", "pest", "🔥"],
        }

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_unserializable_type_raises_error(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试 filter_metadata 包含不可序列化类型（如 datetime）应抛出 TypeError."""
        mock_exists.return_value = True
        mock_chroma_cls.return_value = MagicMock()

        service = get_rag_service()

        # datetime 对象不能直接 JSON 序列化
        with pytest.raises(TypeError) as exc_info:
            service.query(
                "番茄", filter_metadata={"timestamp": datetime.datetime.now()}
            )

        assert "不可 JSON 序列化" in str(exc_info.value) or "not JSON serializable" in str(
            exc_info.value
        )

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_custom_object_raises_error(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试 filter_metadata 包含自定义对象应抛出 TypeError."""
        mock_exists.return_value = True
        mock_chroma_cls.return_value = MagicMock()

        service = get_rag_service()

        # 自定义对象不能 JSON 序列化
        class CustomObject:
            pass

        with pytest.raises(TypeError) as exc_info:
            service.query("番茄", filter_metadata={"obj": CustomObject()})

        assert "不可 JSON 序列化" in str(exc_info.value) or "not JSON serializable" in str(
            exc_info.value
        )

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_cache_hit_with_same_filter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls, sample_documents
    ):
        """测试相同 filter_metadata 能正确命中缓存（第二次查询不调用 similarity_search）."""
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = sample_documents[:1]
        mock_chroma_cls.return_value = mock_db

        service = get_rag_service()

        # 第一次查询 - 会调用 similarity_search
        results1 = service.query("番茄", filter_metadata={"category": "disease"})

        # 第二次相同查询 - lru_cache 命中，不会再次调用 similarity_search
        results2 = service.query("番茄", filter_metadata={"category": "disease"})

        # 验证结果相同
        assert results1 == results2

        # 验证 similarity_search 只被调用了一次（第二次从缓存获取）
        assert mock_db.similarity_search.call_count == 1

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_filter_order_independence(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试 filter_metadata 的键顺序不影响缓存（sort_keys=True）."""
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        service = get_rag_service()

        # 两个字典键顺序不同，但内容相同
        # 由于 sort_keys=True，它们会生成相同的 JSON 字符串，从而命中缓存
        filter1 = {"a": 1, "b": 2, "c": 3}
        filter2 = {"c": 3, "a": 1, "b": 2}

        # 执行查询
        service.query("番茄", filter_metadata=filter1)
        service.query("番茄", filter_metadata=filter2)

        # 验证只调用了一次 similarity_search（第二次查询命中缓存）
        assert mock_db.similarity_search.call_count == 1

        # 验证使用的是正确排序后的 filter 参数
        call_kwargs = mock_db.similarity_search.call_args.kwargs
        assert call_kwargs["filter"] == {"a": 1, "b": 2, "c": 3}

    @patch("app.services.rag_service.Chroma")
    @patch("app.services.rag_service.OpenAIEmbeddings")
    @patch("app.services.rag_service.os.path.exists")
    def test_query_with_complex_nested_filter(
        self, mock_exists, mock_embeddings_cls, mock_chroma_cls
    ):
        """测试复杂的嵌套 filter_metadata 结构."""
        mock_exists.return_value = True
        mock_db = MagicMock()
        mock_db.similarity_search.return_value = []
        mock_chroma_cls.return_value = mock_db

        service = get_rag_service()
        complex_filter = {
            "level1": {
                "level2": {"level3": ["a", "b", "c"]},
                "list": [1, 2, {"nested": "value"}],
            },
            "tags": ["tag1", "tag2"],
            "empty_list": [],
            "number": 42,
            "float_val": 3.14,
            "bool_val": True,
            "null_val": None,
        }

        results = service.query("番茄", filter_metadata=complex_filter)

        assert results == []
        mock_db.similarity_search.assert_called_once()
        call_kwargs = mock_db.similarity_search.call_args.kwargs
        assert call_kwargs["filter"] == complex_filter
