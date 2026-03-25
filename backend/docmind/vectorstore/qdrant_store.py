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
from docmind.core.embedding import EmbeddingParams, get_embedding_model
from docmind.core.exceptions import VectorStoreError
from docmind.core.metadata import META_DOC_ID, META_KB_NAME, META_USER_ID

# Qdrant payload path for the doc_id filter field.
# langchain-qdrant serialises Document.metadata under a "metadata" key in the
# Qdrant payload, so the filter path is always "metadata.<key>".
_QDRANT_DOC_ID_PATH: str = f"metadata.{META_DOC_ID}"

_DISTANCE = Distance.COSINE

_store_cache: dict[str, QdrantVectorStore] = {}
_lock = threading.Lock()


def _make_client() -> QdrantClient:
    """Create a QdrantClient that bypasses system proxy settings.

    Background: httpx (used internally by qdrant-client) respects HTTP_PROXY /
    HTTPS_PROXY environment variables by default (trust_env=True). On developer
    machines running a system proxy (e.g. Clash, Surge), this causes all Qdrant
    requests to be routed through the proxy. Proxy software typically rejects
    localhost destinations, resulting in a ReadTimeout.

    Decision: trust_env=False disables env-based proxy detection entirely.

    Trade-off: if Qdrant is ever moved to an external host that requires a proxy
    to reach, this setting must be revisited and an explicit proxy URL should be
    added to settings instead of relying on the system environment.
    """
    return QdrantClient(url=settings.qdrant.url, trust_env=False)

# Re-export so external imports of VectorStoreError from this module still work.
__all__ = [
    "VectorStoreError",
    "get_vector_store",
    "get_vector_store_for_kb",
    "create_kb_collection",
    "delete_kb_collection",
    "delete_documents_by_doc_id",
    "get_chunks_by_doc_id",
    "kb_collection_name",
]


def kb_collection_name(kb_name: str) -> str:
    """Derive the Qdrant collection name from a knowledge base slug.

    Example: "india" → "docmind_india"
    """
    return f"docmind_{kb_name}"


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
        logger.debug(
            "vectorstore_collection_exists",
            {
                "qdrant_url": settings.qdrant.url,
                "collection": col,
            },
        )
        return

    vector_size = _probe_vector_size(embeddings)

    client.create_collection(
        collection_name=col,
        vectors_config=VectorParams(size=vector_size, distance=_DISTANCE),
    )
    logger.info(
        "vectorstore_collection_created",
        {
            "qdrant_url": settings.qdrant.url,
            "collection": col,
            "vector_size": vector_size,
            "distance": str(_DISTANCE),
        },
    )


def get_vector_store_for_kb(
    kb_name: str,
    embeddings: Embeddings,
) -> QdrantVectorStore:
    """Return a cached QdrantVectorStore for the given knowledge base slug.

    This is the primary entry point for production code.
    The collection name is derived as ``docmind_{kb_name}``.
    """
    return get_vector_store(
        embeddings=embeddings, collection=kb_collection_name(kb_name)
    )


async def create_kb_collection(
    kb_name: str, embedding_params: EmbeddingParams | None = None
) -> int:
    """Create a Qdrant collection for a new knowledge base.

    Called when a knowledge base is created via POST /kb.
    Returns the probed vector dimension so the caller can persist it to the DB.
    Raises VectorStoreError if Qdrant is unreachable.
    """
    col = kb_collection_name(kb_name)
    try:
        emb = get_embedding_model(embedding_params)
        client = _make_client()
        existing = {c.name for c in client.get_collections().collections}
        if col not in existing:
            vector_size = _probe_vector_size(emb)
            client.create_collection(
                collection_name=col,
                vectors_config=VectorParams(size=vector_size, distance=_DISTANCE),
            )
            logger.info(
                "vectorstore_collection_created",
                {
                    "qdrant_url": settings.qdrant.url,
                    "collection": col,
                    "vector_size": vector_size,
                    "distance": str(_DISTANCE),
                },
            )
            return vector_size
        else:
            logger.debug(
                "vectorstore_collection_exists",
                {"qdrant_url": settings.qdrant.url, "collection": col},
            )
            # Probe dimension from existing collection
            info = client.get_collection(col)
            size = info.config.params.vectors.size  # type: ignore[union-attr]
            return int(size)
    except VectorStoreError:
        raise
    except Exception as exc:
        raise VectorStoreError(f"Failed to create collection '{col}': {exc}") from exc


async def delete_kb_collection(kb_name: str) -> None:
    """Drop the Qdrant collection for a knowledge base.

    Called when a knowledge base is deleted via DELETE /kb/{kb_id}.
    Silently succeeds if the collection does not exist.
    """
    col = kb_collection_name(kb_name)
    try:
        client = _make_client()
        existing = {c.name for c in client.get_collections().collections}
        if col in existing:
            client.delete_collection(col)
            logger.info("vectorstore_collection_deleted", {"collection": col})
        # Evict from cache
        with _lock:
            _store_cache.pop(col, None)
    except Exception as exc:
        raise VectorStoreError(f"Failed to delete collection '{col}': {exc}") from exc


def get_chunks_by_doc_id(
    kb_name: str,
    doc_id: str,
    offset: int = 0,
    limit: int = 20,
) -> dict:
    """Fetch paginated chunks (points) for a given document from Qdrant.

    Returns a dict with:
    - ``items``: list of chunk dicts (point_id, content, metadata, char_count)
    - ``total``: total number of points matching this doc_id
    - ``offset`` / ``limit``: echo back for client pagination

    Vectors are intentionally excluded — this is for content inspection only.
    """
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue

    col = kb_collection_name(kb_name)
    # Fields to strip from payload before returning — internal/redundant fields
    _STRIP_KEYS = {META_DOC_ID, META_USER_ID, META_KB_NAME}

    try:
        client = _make_client()

        # Count total matching points
        total = client.count(
            collection_name=col,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key=_QDRANT_DOC_ID_PATH,
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
            exact=True,
        ).count

        # Scroll paginated results (no vectors)
        points, _ = client.scroll(
            collection_name=col,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key=_QDRANT_DOC_ID_PATH,
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
            offset=offset,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        items = []
        for p in points:
            payload = p.payload or {}
            # langchain-qdrant stores text in payload["page_content"] and metadata in payload["metadata"]
            content: str = payload.get("page_content", "")
            meta: dict = {
                k: v
                for k, v in payload.get("metadata", {}).items()
                if k not in _STRIP_KEYS
            }
            items.append(
                {
                    "point_id": str(p.id),
                    "content": content,
                    "char_count": len(content),
                    "metadata": meta,
                }
            )

        return {"items": items, "total": total, "offset": offset, "limit": limit}

    except Exception as exc:
        raise VectorStoreError(
            f"Failed to fetch chunks for doc '{doc_id}' from '{col}': {exc}"
        ) from exc


def delete_documents_by_doc_id(kb_name: str, doc_id: str) -> None:
    """Delete all Qdrant points whose payload contains ``doc_id == doc_id``.

    Called when a user deletes a document via DELETE /ingest/{doc_id}.
    """
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue

    col = kb_collection_name(kb_name)
    try:
        client = _make_client()
        client.delete(
            collection_name=col,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key=_QDRANT_DOC_ID_PATH,
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
        )
        logger.info("vectorstore_doc_deleted", {"collection": col, "doc_id": doc_id})
    except Exception as exc:
        raise VectorStoreError(
            f"Failed to delete doc '{doc_id}' from '{col}': {exc}"
        ) from exc


def get_vector_store(
    embeddings: Embeddings,
    collection: str,
) -> QdrantVectorStore:
    """Build or return a cached QdrantVectorStore instance.

    On first access the collection is checked and auto-created if missing.
    """
    if not collection:
        raise ValueError("collection name must be a non-empty string")
    col = collection
    cache_key = col

    # Fast path — already cached (KB embedding model is immutable after creation)
    cached = _store_cache.get(cache_key)
    if cached is not None:
        return cached

    # Without locking, concurrent threads could all miss the cache and redundantly
    # create multiple instances, causing unnecessary Qdrant connections.
    with _lock:
        # Double-check after acquiring lock
        if cache_key in _store_cache:
            return _store_cache[cache_key]

        try:
            emb = embeddings
            client = _make_client()
            _ensure_collection(client, col, emb)

            store = QdrantVectorStore.from_existing_collection(
                embedding=emb,
                collection_name=col,
                url=settings.qdrant.url,
            )
        except VectorStoreError:
            raise
        except Exception as exc:
            logger.error(
                "vectorstore_connect_failed",
                {
                    "qdrant_url": settings.qdrant.url,
                    "collection": col,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            raise VectorStoreError(
                f"Failed to connect to Qdrant at {settings.qdrant.url} "
                f"(collection={col!r}): {exc}"
            ) from exc

        _store_cache[cache_key] = store

        logger.debug(
            "vectorstore_connected",
            {
                "qdrant_url": settings.qdrant.url,
                "collection": col,
            },
        )
        return store


def reset_store_cache() -> None:
    """Clear the cached vector store instances (useful for testing)."""
    with _lock:
        _store_cache.clear()
