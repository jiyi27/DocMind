"""Embedding model factory — single source of truth for the embedding instance."""

from __future__ import annotations

from langchain_openai import OpenAIEmbeddings

from docmind.core.config import settings


def get_embedding_model() -> OpenAIEmbeddings:
    """Return the configured embedding model.

    Uses any OpenAI-compatible embedding endpoint.
    Switch providers by changing EMBEDDING_BASE_URL / EMBEDDING_MODEL in .env —
    no code changes required.

    Examples:
        Ollama (local):   EMBEDDING_BASE_URL=http://localhost:11434/v1
        OpenAI:           EMBEDDING_BASE_URL=https://api.openai.com/v1
        OpenRouter:       EMBEDDING_BASE_URL=https://openrouter.ai/api/v1
    """
    return OpenAIEmbeddings(
        base_url=settings.embedding.base_url,
        api_key=settings.embedding.api_key,
        model=settings.embedding.model,
    )
