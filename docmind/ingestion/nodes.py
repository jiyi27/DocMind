"""Ingestion graph nodes — each function is a LangGraph node."""

from __future__ import annotations

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from docmind.core.config import settings
from docmind.core import logger
from docmind.ingestion.loaders import load_document
from docmind.ingestion.state import IngestionState
from docmind.vectorstore.qdrant_store import get_vector_store


def load_document_node(state: IngestionState) -> dict:
    """Load documents from the given file path."""
    file_path = state["file_path"]

    try:
        docs = load_document(file_path)
    except Exception as exc:
        logger.error("ingest_load_failed", {
            "file_path": file_path,
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise

    # Inject user-provided metadata into each document
    metadata = state.get("metadata", {})
    for doc in docs:
        doc.metadata.update(metadata)

    return {"documents": docs}


def split_text_node(state: IngestionState) -> dict:
    """Split documents into smaller chunks."""
    try:
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.ingestion.chunk_size,
            chunk_overlap=settings.ingestion.chunk_overlap,
        )
        chunks: list[Document] = splitter.split_documents(state["documents"])
    except Exception as exc:
        logger.error("ingest_split_failed", {
            "doc_count": len(state["documents"]),
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise

    return {"chunks": chunks}


def embed_and_store_node(state: IngestionState) -> dict:
    """Embed chunks and store them in Qdrant."""
    chunks = state["chunks"]

    try:
        store = get_vector_store()
        store.add_documents(chunks)
    except Exception as exc:
        logger.error("ingest_embed_failed", {
            "chunk_count": len(chunks),
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise

    return {"status": "success", "chunk_count": len(chunks)}
