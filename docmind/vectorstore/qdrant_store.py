"""Qdrant vector store wrapper — thin layer over langchain-qdrant.

Provides a cached singleton to avoid reconnecting on every request.
"""

from __future__ import annotations

import threading

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore

from docmind.core.config import settings
from docmind.core import logger
from docmind.core.embedding import get_embedding_model

_store_cache: dict[str, QdrantVectorStore] = {}
_lock = threading.Lock()


class VectorStoreError(Exception):
    """Raised when the vector store cannot be reached or is misconfigured."""


def get_vector_store(
    embeddings: Embeddings | None = None,
    collection: str | None = None,
) -> QdrantVectorStore:
    """Build or return a cached QdrantVectorStore instance.

    Parameters
    ----------
    embeddings:
        Optional override for the embedding model. Defaults to the global Ollama config.
    collection:
        Optional override for the Qdrant collection name. Defaults to env config.

    Raises
    ------
    VectorStoreError
        If the connection to Qdrant fails (e.g. server down, collection missing).
    """
    col = collection or settings.qdrant.collection
    cache_key = col

    # Fast path — already cached
    cached = _store_cache.get(cache_key)
    if cached is not None and embeddings is None:
        return cached

    with _lock:
        # Double-check after acquiring lock
        if cache_key in _store_cache and embeddings is None:
            return _store_cache[cache_key]

        try:
            store = QdrantVectorStore.from_existing_collection(
                embedding=embeddings or get_embedding_model(),
                collection_name=col,
                url=settings.qdrant.url,
            )
        except Exception as exc:
            logger.error("vectorstore_connect_failed", {
                "qdrant_url": settings.qdrant.url,
                "collection": col,
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
            raise VectorStoreError(
                f"Failed to connect to Qdrant at {settings.qdrant.url} "
                f"(collection={col!r}): {exc}"
            ) from exc

        if embeddings is None:
            _store_cache[cache_key] = store

        logger.debug("vectorstore_connected", {
            "qdrant_url": settings.qdrant.url,
            "collection": col,
            "cached": embeddings is None,
        })
        return store


def reset_store_cache() -> None:
    """Clear the cached vector store instances (useful for testing)."""
    with _lock:
        _store_cache.clear()
