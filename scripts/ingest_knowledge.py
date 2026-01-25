#!/usr/bin/env python
"""
Knowledge Base Ingestion Script for Smart-Agriculture RAG System

This script ingests Markdown and PDF documents from a local directory into ChromaDB
for vector storage and retrieval. Uses multi-threading for IO-intensive operations.

Usage:
    # Initial ingestion (creates new database)
    uv run python scripts/ingest_knowledge.py --path data/knowledge/

    # Append to existing database
    uv run python scripts/ingest_knowledge.py --path data/knowledge/ --append

    # Reset database and re-ingest
    uv run python scripts/ingest_knowledge.py --path data/knowledge/ --reset

    # Custom chunk size and max workers
    uv run python scripts/ingest_knowledge.py --path data/knowledge/ \
        --chunk-size 1500 --overlap 300 --max-workers 8

Requirements:
    - OPENAI_API_KEY must be set in .env file
    - ChromaDB will be stored in data/chroma/ by default
"""

import argparse
import logging
import os
import shutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_community.document_loaders import (
    DirectoryLoader,
    PyPDFLoader,
    UnstructuredMarkdownLoader,
)
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
# Qwen/Qwen2-0.5B-Embedding 支持 32k token 限制，可以使用更大的 chunk 保持语义完整
DEFAULT_CHUNK_SIZE = 1500  # 约 750-1000 tokens（中文）
DEFAULT_OVERLAP = 300  # 20% overlap 保持上下文连贯
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", "data/chroma")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")  # 支持硅基流动等 OpenAI 兼容 API
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Ingest knowledge base documents into ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--path",
        type=str,
        default="data/knowledge/",
        help="Path to knowledge base directory (default: data/knowledge/)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing database (default: False, creates new database)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before ingestion (deletes existing data)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Chunk size for text splitting (default: {DEFAULT_CHUNK_SIZE})",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=DEFAULT_OVERLAP,
        help=f"Overlap between chunks (default: {DEFAULT_OVERLAP})",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=8,
        help="Maximum number of threads for concurrent API calls (default: 8)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10,
        help="Number of chunks to process per batch (default: 10)",
    )
    return parser.parse_args()


def check_api_key() -> None:
    """Verify that OpenAI API key is configured."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("sk-"):
        return  # Valid API key (even if it's a placeholder)

    raise ValueError(
        "OPENAI_API_KEY not configured. Please set it in your .env file.\n"
        "Get your API key from: https://platform.openai.com/api-keys"
    )


def reset_database() -> None:
    """Remove existing ChromaDB directory."""
    chroma_path = Path(CHROMA_PERSIST_DIR)
    if chroma_path.exists():
        logger.warning(f"Removing existing ChromaDB at {CHROMA_PERSIST_DIR}")
        shutil.rmtree(chroma_path)
        logger.info("Database reset complete")
    else:
        logger.info("No existing database found, nothing to reset")


def load_documents(knowledge_path: str) -> List:
    """
    Load Markdown and PDF documents from the specified directory.

    Args:
        knowledge_path: Path to knowledge base directory

    Returns:
        List of loaded documents
    """
    logger.info(f"Loading documents from {knowledge_path}")

    # Check if directory exists
    if not Path(knowledge_path).exists():
        raise ValueError(f"Knowledge directory not found: {knowledge_path}")

    # Load Markdown files
    logger.info("Loading Markdown files...")
    md_loader = DirectoryLoader(
        knowledge_path,
        glob="**/*.md",
        loader_cls=UnstructuredMarkdownLoader,
        show_progress=True,
        recursive=True,
    )
    md_docs = md_loader.load()
    logger.info(f"Loaded {len(md_docs)} Markdown documents")

    # Load PDF files
    logger.info("Loading PDF files...")
    pdf_loader = DirectoryLoader(
        knowledge_path,
        glob="**/*.pdf",
        loader_cls=PyPDFLoader,  # type: ignore[arg-type]
        show_progress=True,
        recursive=True,
    )
    pdf_docs = pdf_loader.load()
    logger.info(f"Loaded {len(pdf_docs)} PDF documents")

    all_docs = md_docs + pdf_docs
    logger.info(f"Total documents loaded: {len(all_docs)}")

    if len(all_docs) == 0:
        logger.warning(f"No documents found in {knowledge_path}")
        logger.warning("Supported formats: .md, .pdf")

    return all_docs


def split_documents(
    documents: List,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_OVERLAP,
) -> List:
    """
    Split documents into chunks for vector storage.

    Args:
        documents: List of documents to split
        chunk_size: Maximum size of each chunk
        overlap: Overlap between chunks

    Returns:
        List of document chunks
    """
    logger.info(f"Splitting documents (chunk_size={chunk_size}, overlap={overlap})")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", "。", "！", "？", ". ", " ", ""],
    )

    chunks = text_splitter.split_documents(documents)
    logger.info(f"Created {len(chunks)} chunks from {len(documents)} documents")

    return chunks


def embed_texts_concurrent(
    texts: List[str],
    embeddings: OpenAIEmbeddings,
    max_workers: int = 8,
    batch_size: int = 10,
    show_progress: bool = True,
) -> List[List[float] | None]:
    """
    Embed texts concurrently using ThreadPoolExecutor for IO-intensive operations.

    Args:
        texts: List of text strings to embed
        embeddings: OpenAIEmbeddings instance
        max_workers: Maximum number of concurrent threads
        batch_size: Number of texts to process per batch
        show_progress: Whether to show progress logs

    Returns:
        List of embedding vectors
    """
    import threading

    results: List[List[float] | None] = [None] * len(texts)  # type: ignore[list-item]
    completed_count = 0
    lock = threading.Lock()

    def embed_batch(batch_indices: List[int]) -> None:
        """Embed a batch of texts."""
        nonlocal completed_count
        batch_texts = [texts[i] for i in batch_indices]

        try:
            # Use OpenAI embed_documents (handles batching internally)
            batch_embeddings = embeddings.embed_documents(batch_texts)

            for idx, embedding in zip(batch_indices, batch_embeddings):
                results[idx] = embedding

            with lock:
                completed_count += len(batch_indices)
                if show_progress and completed_count % 10 == 0:
                    logger.info(f"  Embedded {completed_count}/{len(texts)} chunks")

        except Exception as e:
            logger.error(f"Error embedding batch starting at index {batch_indices[0]}: {str(e)}")
            # Set empty embeddings for failed batch
            for idx in batch_indices:
                results[idx] = []

    # Split indices into batches
    batch_indices_list = [
        list(range(i, min(i + batch_size, len(texts))))
        for i in range(0, len(texts), batch_size)
    ]

    logger.info(
        f"Embedding {len(texts)} chunks with {max_workers} workers "
        f"(batch_size={batch_size})..."
    )

    # Process batches concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(embed_batch, batch_idx) for batch_idx in batch_indices_list]

        for future in as_completed(futures):
            try:
                future.result()  # Will raise exception if embed_batch failed
            except Exception as e:
                logger.error(f"Batch processing failed: {str(e)}")

    # Verify all results are filled
    if None in results:
        raise ValueError("Some embeddings failed to generate")

    if show_progress:
        logger.info(f"  ✅ Successfully embedded {len(texts)} chunks")

    return results


def create_vector_store(
    chunks: List,
    append: bool = False,
    max_workers: int = 8,
    batch_size: int = 10,
) -> Chroma:
    """
    Create or update ChromaDB vector store with document chunks.

    Args:
        chunks: List of document chunks to ingest
        append: If True, append to existing database; if False, create new
        max_workers: Maximum number of concurrent threads for embeddings
        batch_size: Number of chunks to process per batch

    Returns:
        ChromaDB vector store instance
    """
    logger.info(f"Initializing OpenAI Embeddings ({OPENAI_EMBEDDING_MODEL})...")

    # 支持硅基流动等 OpenAI 兼容 API
    if OPENAI_BASE_URL:
        logger.info(f"Using custom base URL: {OPENAI_BASE_URL}")
        logger.info(f"Using embedding model: {OPENAI_EMBEDDING_MODEL}")
        embeddings = OpenAIEmbeddings(
            model=OPENAI_EMBEDDING_MODEL,
            base_url=OPENAI_BASE_URL,
        )
    else:
        embeddings = OpenAIEmbeddings(model=OPENAI_EMBEDDING_MODEL)

    # Extract text content from chunks
    texts = [chunk.page_content for chunk in chunks]
    metadatas = [chunk.metadata for chunk in chunks]

    # Generate embeddings concurrently
    embedding_vectors = embed_texts_concurrent(
        texts=texts,
        embeddings=embeddings,
        max_workers=max_workers,
        batch_size=batch_size,
        show_progress=True,
    )

    # Create or update ChromaDB
    if append and Path(CHROMA_PERSIST_DIR).exists():
        logger.info(f"Appending to existing database at {CHROMA_PERSIST_DIR}")
        vector_store = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings,
        )
        # Add texts with pre-computed embeddings
        vector_store.add_texts(texts=texts, embeddings=embedding_vectors, metadatas=metadatas)
    else:
        logger.info(f"Creating new database at {CHROMA_PERSIST_DIR}")
        # Create new collection with pre-computed embeddings
        vector_store = Chroma(
            embedding_function=embeddings,
            persist_directory=CHROMA_PERSIST_DIR,
        )
        vector_store.add_texts(texts=texts, embeddings=embedding_vectors, metadatas=metadatas)

    return vector_store


def main() -> None:
    """Main ingestion workflow."""
    args = parse_args()

    logger.info("=" * 60)
    logger.info("Smart-Agriculture Knowledge Base Ingestion")
    logger.info("=" * 60)

    start_time = time.time()

    try:
        # Step 1: Check API key
        logger.info("Step 1: Verifying OpenAI API key...")
        check_api_key()
        logger.info("✓ API key configured\n")

        # Step 2: Reset database if requested
        if args.reset:
            logger.info("Step 2: Resetting database...")
            reset_database()
            print()

        # Step 3: Load documents
        logger.info("Step 3: Loading documents...")
        documents = load_documents(args.path)

        if len(documents) == 0:
            logger.error("No documents to ingest. Exiting.")
            return

        print()

        # Step 4: Split documents
        logger.info("Step 4: Splitting documents into chunks...")
        chunks = split_documents(documents, args.chunk_size, args.overlap)
        print()

        # Step 5: Create vector store
        logger.info("Step 5: Creating ChromaDB vector store...")
        logger.info(f"Using {args.max_workers} concurrent workers for embeddings...")
        logger.info("(This may take a few minutes for large document sets...)")
        create_vector_store(
            chunks,
            append=args.append,
            max_workers=args.max_workers,
            batch_size=args.batch_size,
        )
        print()

        # Step 6: Summary
        elapsed_time = time.time() - start_time
        logger.info("=" * 60)
        logger.info("Ingestion Complete!")
        logger.info("=" * 60)
        logger.info(f"✅ Processed files: {len(documents)}")
        logger.info(f"✅ Created chunks: {len(chunks)}")
        logger.info(f"✅ Stored in ChromaDB: {CHROMA_PERSIST_DIR}")
        logger.info(f"✅ Time elapsed: {elapsed_time:.1f}s")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"\n❌ Ingestion failed: {str(e)}")
        logger.error("Please check the error messages above and try again.")
        raise


if __name__ == "__main__":
    main()
