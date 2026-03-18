"""RAG chat graph nodes — retrieve and generate."""

from __future__ import annotations

from typing import AsyncGenerator

from langchain_core.messages import AnyMessage, HumanMessage

from docmind.core import logger
from docmind.core.config import settings
from docmind.core.llm import get_llm
from docmind.ingestion.constants import DEFAULT_RETRIEVAL_MODE
from docmind.ingestion.loaders import load_document
from docmind.retrieval.prompts import rag_prompt
from docmind.retrieval.state import RAGState
from docmind.vectorstore.qdrant_store import get_vector_store_for_kb


def _load_full_text(file_path: str) -> str:
    """Load a document from disk and return its full text content.

    For PDFs this joins all pages; for Markdown this returns the single document.
    """
    docs = load_document(file_path)
    return "\n\n".join(d.page_content for d in docs)


def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant documents from Qdrant based on the user query.

    Workflow:
    - Qdrant similarity search with scores (topK configured via settings)
    - Greedy selection:
        - chunk docs: always included
        - full_doc docs: deduped by doc_id, capped at max_full_docs; full text
          loaded from disk and truncated to max_full_doc_chars
    - Formats retrieved docs into context string and citation sources
    """
    query = state["query"]
    kb_name = state["kb_name"]

    try:
        store = get_vector_store_for_kb(kb_name)
        results = store.similarity_search_with_score(query, k=settings.retrieval.top_k)
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

    max_full_docs = settings.retrieval.max_full_docs
    max_full_doc_chars = settings.retrieval.max_full_doc_chars

    context_parts: list[str] = []
    sources: list[str] = []
    retrieved_docs = []

    seen_full_doc_ids: set[str] = set()
    full_doc_count = 0

    for doc, _score in results:
        meta = doc.metadata or {}
        retrieval_mode = meta.get("retrieval_mode", DEFAULT_RETRIEVAL_MODE)

        if retrieval_mode == "full_doc":
            doc_id = meta.get("doc_id", "")
            if doc_id in seen_full_doc_ids:
                continue
            if full_doc_count >= max_full_docs:
                continue

            file_path = meta.get("file_path", "")
            if not file_path:
                logger.warning(
                    "full_doc_missing_file_path",
                    {"doc_id": doc_id, "kb_name": kb_name},
                )
                continue

            try:
                full_text = _load_full_text(file_path)
            except Exception as exc:
                logger.warning(
                    "full_doc_load_failed",
                    {
                        "doc_id": doc_id,
                        "file_path": file_path,
                        "error": str(exc),
                    },
                )
                continue

            if len(full_text) > max_full_doc_chars:
                full_text = full_text[:max_full_doc_chars]

            context_content = full_text
            seen_full_doc_ids.add(doc_id)
            full_doc_count += 1
        else:
            # Determine if we should use original code or the indexed summary
            if meta.get("chunk_type") == "code" and "original_code" in meta:
                context_content = meta["original_code"]
            else:
                context_content = doc.page_content

        i = len(context_parts) + 1
        context_parts.append(f"[{i}] {context_content}")
        retrieved_docs.append(doc)

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
        "retrieved_docs": retrieved_docs,
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
