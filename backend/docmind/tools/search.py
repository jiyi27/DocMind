"""Qdrant semantic search tool.

Wrapped as a LangChain @tool so it can be used directly by a LangGraph
agent node when the system evolves from fixed-flow to agentic mode.
"""

from __future__ import annotations

from langchain_core.tools import tool

from docmind.core.config import settings
from docmind.vectorstore.qdrant_store import get_vector_store


@tool
def search_knowledge_base(query: str) -> str:
    """Search the knowledge base for information relevant to the query.

    Returns the top-k most relevant document chunks with their sources.
    """
    from docmind.core import logger

    try:
        store = get_vector_store()
        docs = store.similarity_search(query, k=settings.retrieval.top_k)
    except Exception as exc:
        logger.error("tool_search_failed", {
            "query": query[:200],
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        return "Knowledge base search is currently unavailable. Please try again later."

    if not docs:
        return "No relevant documents found."

    results: list[str] = []
    for i, doc in enumerate(docs, 1):
        meta = doc.metadata or {}
        title = meta.get("title") or meta.get("file_name") or "unknown"
        results.append(f"[{i}] ({title}): {doc.page_content}")

    return "\n\n".join(results)
