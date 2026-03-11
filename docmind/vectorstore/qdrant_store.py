"""Qdrant vector store wrapper — thin layer over langchain-qdrant."""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_qdrant import QdrantVectorStore

from docmind.core.config import settings
from docmind.core.embedding import get_embedding_model


def get_vector_store(
    embeddings: Embeddings | None = None,
    collection: str | None = None,
) -> QdrantVectorStore:
    """Build a QdrantVectorStore instance.

    Parameters
    ----------
    embeddings:
        Optional override for the embedding model. Defaults to the global Ollama config.
    collection:
        Optional override for the Qdrant collection name. Defaults to env config.
    """
    return QdrantVectorStore.from_existing_collection(
        embedding=embeddings or get_embedding_model(),
        collection_name=collection or settings.qdrant.collection,
        url=settings.qdrant.url,
    )
