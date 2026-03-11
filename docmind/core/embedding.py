"""Embedding model factory — single source of truth for the embedding instance."""

from __future__ import annotations

from langchain_community.embeddings import OllamaEmbeddings

from docmind.core.config import settings


def get_embedding_model() -> OllamaEmbeddings:
    """Return the configured Ollama embedding model.

    Uses nomic-embed-text by default, matching the n8n workflow.
    """
    return OllamaEmbeddings(
        base_url=settings.ollama.base_url,
        model=settings.ollama.model,
    )
