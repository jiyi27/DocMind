"""Text splitter configuration — matches n8n RecursiveCharacterTextSplitter."""

from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from docmind.core.config import settings


def get_text_splitter() -> RecursiveCharacterTextSplitter:
    """Return a text splitter using the configured chunk_size and chunk_overlap."""
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.ingestion.chunk_size,
        chunk_overlap=settings.ingestion.chunk_overlap,
    )
