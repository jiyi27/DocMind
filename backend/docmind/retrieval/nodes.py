"""RAG chat graph nodes — retrieve and generate."""

from __future__ import annotations

from typing import AsyncGenerator

from langchain_core.messages import AnyMessage, HumanMessage

from docmind.core import logger
from docmind.core.config import settings
from docmind.core.llm import get_llm
from docmind.retrieval.prompts import rag_prompt
from docmind.retrieval.state import RAGState
from docmind.vectorstore.qdrant_store import get_vector_store_for_kb


def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant documents from Qdrant based on the user query.

    Workflow:
    - Qdrant Vector Store similarity search (topK configured via settings)
    - Formats retrieved docs into context string and citation sources
    """
    query = state["query"]
    kb_name = state["kb_name"]

    try:
        store = get_vector_store_for_kb(kb_name)
        docs = store.similarity_search(query, k=settings.retrieval.top_k)
    except Exception as exc:
        logger.error(
            "retrieval_search_failed",
            {
                "query": query[:200],
                "kb_name": kb_name,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
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
    """Generate an answer using the LLM with retrieved context and conversation history.

    The caller injects the full prior history via state["messages"]. This node
    appends the current HumanMessage and invokes the LLM, then returns only the
    generated answer. Persistence is handled upstream by the chat router.
    """
    try:
        llm = get_llm()
        chain = rag_prompt | llm

        # History is pre-truncated by the chat router before being passed in.
        # Append the current turn and invoke the LLM.
        messages = list(state.get("messages", []))
        messages.append(HumanMessage(content=state["query"]))

        result = chain.invoke(
            {
                "context": state.get("context", ""),
                "sources": "\n".join(state.get("sources", [])),
                "messages": messages,
            }
        )
    except Exception as exc:
        logger.error(
            "retrieval_generate_failed",
            {
                "query": state["query"][:200],
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    return {"answer": result.content}


def retrieve(query: str, kb_name: str) -> tuple[str, list[str]]:
    """Run retrieval synchronously and return (context, sources).

    Extracted as a standalone function for use by the streaming chat endpoint,
    which bypasses the LangGraph graph and drives retrieval + generation directly.
    """
    state: RAGState = {"query": query, "kb_name": kb_name}
    result = retrieve_node(state)
    return result["context"], result["sources"]


async def stream_generate(
    query: str,
    context: str,
    sources: list[str],
    messages: list[AnyMessage],
) -> AsyncGenerator[str, None]:
    """Stream LLM token chunks for the given query + RAG context.

    Yields raw text fragments (not SSE-formatted). The caller is responsible
    for wrapping chunks in SSE lines and flushing them to the HTTP response.

    Parameters
    ----------
    query:
        The current user question.
    context:
        Formatted retrieval context assembled by ``retrieve()``.
    sources:
        Source citation strings assembled by ``retrieve()``.
    messages:
        Prior conversation history (LangChain message objects), already
        truncated by the caller to MAX_MESSAGES.
    """
    llm = get_llm()
    chain = rag_prompt | llm

    lc_messages = list(messages)
    lc_messages.append(HumanMessage(content=query))

    try:
        async for chunk in chain.astream(
            {
                "context": context,
                "sources": "\n".join(sources),
                "messages": lc_messages,
            }
        ):
            text = chunk.content
            if text:
                yield text
    except Exception as exc:
        logger.error(
            "retrieval_stream_failed",
            {
                "query": query[:200],
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise
