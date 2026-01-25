"""
RAG Service for Smart-Agriculture Diagnosis System

This module provides vector retrieval capabilities from ChromaDB for generating
context-aware diagnosis reports using retrieved agricultural knowledge.

Usage:
    from app.services.rag_service import get_rag_service

    rag = get_rag_service()
    docs = rag.query("番茄白粉病", top_k=3)
"""

import json
import logging
import os
from functools import lru_cache
from typing import Dict, List, Optional

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Configuration
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", "data/chroma")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


class RAGServiceNotInitializedError(Exception):
    """Raised when RAG service is accessed before ChromaDB is initialized."""

    pass


class RAGService:
    """
    Singleton service for retrieving relevant documents from ChromaDB.

    This service provides semantic search capabilities over the agricultural
    knowledge base using vector embeddings.
    """

    _instance: Optional["RAGService"] = None

    def __new__(cls) -> "RAGService":
        """Implement singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize RAG service (lazily on first query)."""
        if self._initialized:
            return

        self._chroma_db: Optional[Chroma] = None
        self._embeddings: Optional[OpenAIEmbeddings] = None
        self._initialized = True
        logger.info("RAG Service singleton created")

    def _get_chroma_db(self) -> Chroma:
        """
        Load ChromaDB instance from persistent storage.

        Returns:
            ChromaDB vector store instance

        Raises:
            RAGServiceNotInitializedError: If database directory doesn't exist
        """
        if self._chroma_db is not None:
            return self._chroma_db

        chroma_path = CHROMA_PERSIST_DIR
        if not os.path.exists(chroma_path):
            raise RAGServiceNotInitializedError(
                f"ChromaDB not initialized at {chroma_path}. "
                f"Please run: uv run python scripts/ingest_knowledge.py --path data/knowledge/"
            )

        logger.info(f"Loading ChromaDB from {chroma_path}")

        # Initialize embeddings
        if OPENAI_BASE_URL:
            logger.info(f"Using custom base URL: {OPENAI_BASE_URL}")
            logger.info(f"Using embedding model: {OPENAI_EMBEDDING_MODEL}")
            self._embeddings = OpenAIEmbeddings(
                model=OPENAI_EMBEDDING_MODEL,
                base_url=OPENAI_BASE_URL,
            )
        else:
            self._embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)

        # Load ChromaDB
        self._chroma_db = Chroma(
            persist_directory=chroma_path,
            embedding_function=self._embeddings,
        )

        logger.info("ChromaDB loaded successfully")
        return self._chroma_db

    def query(
        self,
        query_text: str,
        top_k: int = 3,
        filter_metadata: Optional[Dict] = None,
    ) -> List[Document]:
        """
        Retrieve relevant documents using semantic search.

        Args:
            query_text: Query text (e.g., disease name, symptom description)
            top_k: Number of relevant documents to retrieve (default: 3)
            filter_metadata: Optional metadata filter (e.g., {"category": "diseases"})
                           支持 JSON 可序列化类型：str, int, float, bool, list, dict, None
                           不支持 datetime、自定义对象等非 JSON 类型

        Returns:
            List of relevant Document objects, sorted by relevance

        Raises:
            RAGServiceNotInitializedError: If ChromaDB is not initialized
            ValueError: If query_text is empty
            TypeError: If filter_metadata 包含不可序列化的类型（如 datetime、自定义对象）

        Example:
            >>> rag = get_rag_service()
            >>> docs = rag.query("番茄晚疫病", top_k=3)
            >>> for doc in docs:
            ...     print(f"{doc.metadata['source']}: {doc.page_content[:100]}")
        """
        if not query_text or not query_text.strip():
            raise ValueError("query_text cannot be empty")

        # 将 filter_metadata 转换为 JSON 字符串用于缓存
        # JSON 序列化支持列表、嵌套字典等复杂结构，避免 tuple() 的不可哈希问题
        # sort_keys=True 确保 {"a":1, "b":2} 和 {"b":2, "a":1} 生成相同的缓存 key
        try:
            filter_json = (
                json.dumps(filter_metadata, sort_keys=True)
                if filter_metadata is not None
                else None
            )
        except (TypeError, ValueError) as e:
            # 捕获不可序列化的类型（如 datetime、自定义对象）
            raise TypeError(
                f"filter_metadata 包含不可 JSON 序列化的类型: {e}. "
                "仅支持 str, int, float, bool, list, dict, None"
            ) from e

        return self._cached_search(query_text, top_k, filter_json)

    @lru_cache(maxsize=100)
    def _cached_search(
        self,
        query_text: str,
        top_k: int,
        filter_json: Optional[str],
    ) -> List[Document]:
        """
        缓存的相似度搜索实现（使用 JSON 字符串作为缓存 key）。

        Args:
            query_text: 查询文本
            top_k: 返回结果数量
            filter_json: JSON 序列化后的 filter_metadata 字符串（用于缓存 key）
        """
        logger.info(f"Querying ChromaDB: '{query_text}' (top_k={top_k})")

        # 将 JSON 字符串转换回字典用于 ChromaDB 查询
        try:
            filter_metadata = (
                json.loads(filter_json) if filter_json is not None else None
            )
        except json.JSONDecodeError as e:
            # 理论上不会发生，因为 filter_json 是由我们自己序列化的
            logger.error(f"Failed to deserialize filter_json: {e}")
            filter_metadata = None

        if filter_metadata:
            logger.info(f"Filter metadata: {filter_metadata}")

        try:
            chroma_db = self._get_chroma_db()

            # Perform similarity search
            if filter_metadata:
                results = chroma_db.similarity_search(
                    query_text,
                    k=top_k,
                    filter=filter_metadata,
                )
            else:
                results = chroma_db.similarity_search(query_text, k=top_k)

            logger.info(f"Retrieved {len(results)} documents")
            for i, doc in enumerate(results):
                logger.debug(f"  [{i+1}] {doc.metadata.get('source', 'unknown')}")

            return results

        except Exception as e:
            logger.error(f"Failed to query ChromaDB: {str(e)}")
            raise


# Module-level singleton instance
_rag_service_instance: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """
    Get the singleton RAG service instance.

    This function implements lazy initialization - the ChromaDB connection
    is established on the first call.

    Returns:
        RAGService singleton instance

    Example:
        >>> from app.services.rag_service import get_rag_service
        >>> rag = get_rag_service()
        >>> docs = rag.query("番茄白粉病", top_k=3)
    """
    global _rag_service_instance

    if _rag_service_instance is None:
        logger.info("Initializing RAG Service singleton...")
        _rag_service_instance = RAGService()

    return _rag_service_instance


def reset_rag_service() -> None:
    """
    Reset the RAG service singleton.

    This is primarily used for testing purposes.

    Warning:
        This should not be called in production code.
    """
    global _rag_service_instance
    _rag_service_instance = None
    # Also reset the class-level singleton
    RAGService._instance = None
    logger.warning("RAG Service singleton has been reset")
