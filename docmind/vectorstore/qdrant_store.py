"""Qdrant vector store wrapper — thin layer over langchain-qdrant.

Provides a cached singleton to avoid reconnecting on every request.
Auto-creates the configured collection if it does not exist.
"""

from __future__ import annotations

import threading

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from docmind.core.config import settings
from docmind.core import logger
from docmind.core.embedding import get_embedding_model
from docmind.core.exceptions import VectorStoreError

_DISTANCE = Distance.COSINE

_store_cache: dict[str, QdrantVectorStore] = {}
_lock = threading.Lock()

# Re-export so external imports of VectorStoreError from this module still work.
__all__ = ["VectorStoreError", "get_vector_store"]


def _probe_vector_size(embeddings: Embeddings) -> int:
    """Dynamically determine the embedding dimension by encoding a test string.

    This avoids hardcoding a vector size that may differ across models
    (e.g. nomic-embed-text=768, text-embedding-3-small=1536, etc.).
    """
    vector = embeddings.embed_query("probe")
    return len(vector)


def _ensure_collection(client: QdrantClient, col: str, embeddings: Embeddings) -> None:
    """Check if *col* exists in Qdrant; create it with the correct vector size if not.

    The vector dimension is probed dynamically from the embedding model so that
    switching models (e.g. nomic-embed-text → text-embedding-3-small) requires
    no code changes — only an .env update.

    Note: dimension/distance mismatch on existing collections is already handled
    by langchain-qdrant `from_existing_collection` (validate_collection_config=True).
    """
    existing = {c.name for c in client.get_collections().collections}
    if col in existing:
        logger.debug("vectorstore_collection_exists", {
            "qdrant_url": settings.qdrant.url,
            "collection": col,
        })
        return

    vector_size = _probe_vector_size(embeddings)

    client.create_collection(
        collection_name=col,
        vectors_config=VectorParams(size=vector_size, distance=_DISTANCE),
    )
    logger.info("vectorstore_collection_created", {
        "qdrant_url": settings.qdrant.url,
        "collection": col,
        "vector_size": vector_size,
        "distance": str(_DISTANCE),
        "embedding_model": settings.embedding.model,
    })


def get_vector_store(
    embeddings: Embeddings | None = None,
    collection: str | None = None,
) -> QdrantVectorStore:
    """Build or return a cached QdrantVectorStore instance.

    On first access the collection is checked and auto-created if missing.

    Parameters
    ----------
    embeddings:
        Optional override for the embedding model. Defaults to the global Ollama config.
    collection:
        Optional override for the Qdrant collection name. Defaults to env config.

    Raises
    ------
    VectorStoreError
        If the connection to Qdrant fails (e.g. server down).
    """
    col = collection or settings.qdrant.collection
    cache_key = col

    # Fast path — already cached
    cached = _store_cache.get(cache_key)
    if cached is not None and embeddings is None:
        return cached

    # Without locking, concurrent threads could all miss the cache and redundantly
    # create multiple instances, causing unnecessary Qdrant connections.
    with _lock:
        # Double-check after acquiring lock
        if cache_key in _store_cache and embeddings is None:
            return _store_cache[cache_key]

        try:
            emb = embeddings or get_embedding_model()
            client = QdrantClient(url=settings.qdrant.url)
            _ensure_collection(client, col, emb)

            store = QdrantVectorStore.from_existing_collection(
                embedding=emb,
                collection_name=col,
                url=settings.qdrant.url,
            )
        except VectorStoreError:
            raise
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
