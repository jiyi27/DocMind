"""Embedding model factory — per-KB embedding configuration with dict-based cache."""

from __future__ import annotations

import sqlite3
import threading
from dataclasses import dataclass

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from docmind.core import logger
from docmind.core.exceptions import ConfigError
from docmind.db.database import get_db_path

# Legacy alias kept for any existing catch sites.
EmbeddingConfigError = ConfigError


@dataclass(frozen=True)
class EmbeddingParams:
    """Immutable, hashable embedding configuration (used as cache key)."""

    provider: str  # 'openai_compatible' | 'huggingface'
    base_url: str
    api_key: str
    model: str


_embedding_cache: dict[EmbeddingParams, Embeddings] = {}
_lock = threading.Lock()


def _build_embedding(params: EmbeddingParams) -> Embeddings:
    if params.provider == "openai_compatible":
        return OpenAIEmbeddings(
            base_url=params.base_url,
            api_key=params.api_key,
            model=params.model,
            check_embedding_ctx_length=False,
            tiktoken_enabled=False,
        )
    elif params.provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings  # lazy import

        return HuggingFaceEmbeddings(model_name=params.model)
    else:
        raise ConfigError(f"Unknown embedding provider: {params.provider!r}")


def get_embedding_model(params: EmbeddingParams) -> Embeddings:
    """Return a cached Embeddings instance for the given params."""
    resolved = params

    cached = _embedding_cache.get(resolved)
    if cached is not None:
        return cached

    with _lock:
        cached = _embedding_cache.get(resolved)
        if cached is not None:
            return cached

        instance = _build_embedding(resolved)
        _embedding_cache[resolved] = instance
        return instance


def get_embedding_for_kb(kb_name: str) -> Embeddings:
    """Return the Embeddings instance bound to a specific knowledge base.

    Reads the KB's persisted embedding config from SQLite (sync connection).
    Legacy KB rows without a fully backfilled config now fail fast instead of
    silently falling back to global defaults, which would risk vector drift.
    """
    try:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT embedding_provider, embedding_model, embedding_base_url, embedding_api_key "
            "FROM knowledge_bases WHERE name = ?",
            (kb_name,),
        )
        row = cur.fetchone()
        conn.close()
    except Exception as exc:
        logger.error(
            "embedding_kb_lookup_failed",
            {"kb_name": kb_name, "error": str(exc)},
        )
        raise ConfigError(
            f"Failed to load embedding configuration for knowledge base '{kb_name}'."
        ) from exc

    if row is None:
        raise ConfigError(
            f"Knowledge base '{kb_name}' does not exist or has no embedding configuration."
        )

    provider = (row["embedding_provider"] or "").strip()
    model = (row["embedding_model"] or "").strip()
    base_url = (row["embedding_base_url"] or "").strip()
    api_key = (row["embedding_api_key"] or "").strip()

    if not provider:
        raise ConfigError(
            f"Knowledge base '{kb_name}' is missing embedding provider configuration."
        )
    if not model:
        raise ConfigError(
            f"Knowledge base '{kb_name}' is missing embedding model configuration."
        )
    if provider == "openai_compatible":
        if not base_url:
            raise ConfigError(
                f"Knowledge base '{kb_name}' is missing embedding base URL configuration."
            )
        if not api_key:
            raise ConfigError(
                f"Knowledge base '{kb_name}' is missing embedding API key configuration."
            )

    params = EmbeddingParams(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )
    return get_embedding_model(params)
