"""RAG chat graph nodes — retrieve and generate."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage

from docmind.core.config import settings
from docmind.core import logger
from docmind.core.llm import get_llm
from docmind.retrieval.prompts import rag_prompt
from docmind.retrieval.state import RAGState
from docmind.vectorstore.qdrant_store import get_vector_store


def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant documents from Qdrant based on the user query.

    Workflow:
    - Qdrant Vector Store (mode=load, topK=3)
    - Code node that formats context + sources
    """
    query = state["query"]

    try:
        store = get_vector_store()
        docs = store.similarity_search(query, k=settings.retrieval.top_k)
    except Exception as exc:
        logger.error("retrieval_search_failed", {
            "query": query[:200],
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise

    # Build formatted context & sources
    context_parts: list[str] = []
    sources: list[str] = []

    for i, doc in enumerate(docs, 1):
        context_parts.append(f"[{i}] {doc.page_content}")

        meta = doc.metadata or {}
        url = meta.get("url", "")
        title = meta.get("title") or meta.get("file_name") or meta.get("source", "")

        if url and title:
            sources.append(f"[{i}] [{title}]({url})")
        elif url:
            sources.append(f"[{i}] [{url}]({url})")
        elif title:
            sources.append(f"[{i}] {title}")
        else:
            sources.append(f"[{i}] unknown source")

    return {
        "retrieved_docs": docs,
        "context": "\n\n".join(context_parts),
        "sources": sources,
    }


def generate_node(state: RAGState) -> dict:
    """Generate an answer using the LLM with retrieved context.

    Uses OpenRouter-compatible ChatOpenAI via get_llm() factory.
    """
    try:
        llm = get_llm()

        # Build the prompt with context, sources, and conversation history
        chain = rag_prompt | llm

        # The user's current query is appended to messages
        messages = list(state.get("messages", []))
        messages.append(HumanMessage(content=state["query"]))

        result = chain.invoke({
            "context": state.get("context", ""),
            "sources": "\n".join(state.get("sources", [])),
            "messages": messages,
        })
    except Exception as exc:
        logger.error("retrieval_generate_failed", {
            "query": state["query"][:200],
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise

    new_messages = [
        HumanMessage(content=state["query"]),
        AIMessage(content=result.content),
    ]

    # Trim conversation history: keep only the most recent max_messages entries.
    # Trimming is applied after appending so the latest exchange is always retained.
    max_messages = settings.retrieval.max_messages
    all_messages = list(state.get("messages", [])) + new_messages
    if max_messages > 0 and len(all_messages) > max_messages:
        all_messages = all_messages[-max_messages:]

    return {
        "answer": result.content,
        "messages": all_messages,
    }
