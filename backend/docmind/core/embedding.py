"""Embedding model factory — single source of truth for the embedding instance.

Uses a cached singleton to avoid re-creating the client on every call.
"""

from __future__ import annotations

import threading

from langchain_openai import OpenAIEmbeddings

from docmind.core.config import settings
from docmind.core import logger
from docmind.core.exceptions import ConfigError

_embedding_instance: OpenAIEmbeddings | None = None
_lock = threading.Lock()

# Legacy alias kept for any existing catch sites.
EmbeddingConfigError = ConfigError


def get_embedding_model() -> OpenAIEmbeddings:
    """Return the configured embedding model (cached singleton).

    Uses any OpenAI-compatible embedding endpoint.
    Switch providers by changing EMBEDDING_BASE_URL / EMBEDDING_MODEL in .env —
    no code changes required.

    Examples:
        Ollama (local):   EMBEDDING_BASE_URL=http://localhost:11434/v1
        OpenAI:           EMBEDDING_BASE_URL=https://api.openai.com/v1
        OpenRouter:       EMBEDDING_BASE_URL=https://openrouter.ai/api/v1

    Raises
    ------
    EmbeddingConfigError
        If EMBEDDING_BASE_URL is empty.
    """
    global _embedding_instance

    if _embedding_instance is not None:
        return _embedding_instance

    with _lock:
        if _embedding_instance is not None:
            return _embedding_instance

        if not settings.embedding.base_url:
            logger.error(
                "embedding_init_failed",
                {"reason": "EMBEDDING_BASE_URL is not configured"},
            )
            raise ConfigError(
                "EMBEDDING_BASE_URL is not configured. Please set it in your environment."
            )

        _embedding_instance = OpenAIEmbeddings(
            base_url=settings.embedding.base_url,
            api_key=settings.embedding.api_key,
            model=settings.embedding.model,
            # Disable tiktoken-based chunking: non-OpenAI providers (e.g. Ollama)
            # only accept plain strings, not token-ID integer arrays.
            check_embedding_ctx_length=False,
            tiktoken_enabled=False,
        )
        return _embedding_instance
