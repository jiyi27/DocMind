"""Ingestion graph nodes — each function is a LangGraph node."""

from __future__ import annotations

from langchain_core.documents import Document

from docmind.ingestion.loaders import load_document
from docmind.ingestion.splitters import get_text_splitter
from docmind.ingestion.state import IngestionState
from docmind.vectorstore.qdrant_store import get_vector_store


def load_document_node(state: IngestionState) -> dict:
    """Load documents from the given file path."""
    docs = load_document(state["file_path"])

    # Inject user-provided metadata into each document
    metadata = state.get("metadata", {})
    for doc in docs:
        doc.metadata.update(metadata)

    return {"documents": docs}


def split_text_node(state: IngestionState) -> dict:
    """Split documents into smaller chunks."""
    splitter = get_text_splitter()
    chunks: list[Document] = splitter.split_documents(state["documents"])
    return {"chunks": chunks}


def embed_and_store_node(state: IngestionState) -> dict:
    """Embed chunks and store them in Qdrant."""
    chunks = state["chunks"]
    store = get_vector_store()
    store.add_documents(chunks)
    return {"status": "success", "chunk_count": len(chunks)}
