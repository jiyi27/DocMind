"""RAG chat graph nodes — retrieve and generate."""

from __future__ import annotations

from typing import AsyncGenerator

from langchain_core.documents import Document
from langchain_core.messages import AnyMessage, HumanMessage

from docmind.core import logger
from docmind.core.config import settings
from docmind.core.llm import get_llm
from docmind.core.metadata import (
    CHUNK_TYPE_CODE_MIXED,
    CHUNK_TYPE_IMAGE,
    DEFAULT_RETRIEVAL_MODE,
    META_CHUNK_TYPE,
    META_DOC_ID,
    META_FILE_NAME,
    META_FILE_PATH,
    META_IMAGE_URL,
    META_ORIGINAL_CONTENT,
    META_RETRIEVAL_MODE,
    META_SOURCE,
    META_TITLE,
    META_URL,
    RETRIEVAL_MODE_FULL_DOC,
)
from docmind.ingestion.loaders import load_document
from docmind.retrieval.context import ContextItem
from docmind.retrieval.prompts import rag_prompt
from docmind.retrieval.state import RAGState
from docmind.core.embedding import get_embedding_for_kb
from docmind.vectorstore.qdrant_store import get_vector_store_for_kb


def _load_full_text(file_path: str) -> str:
    """Load a document from disk and return its full text content.

    For PDFs this joins all pages; for Markdown this returns the single document.
    """
    docs = load_document(file_path)
    return "\n\n".join(d.page_content for d in docs)


def _build_source_label(index: int, title: str, url: str) -> str:
    """Format a single citation line from index, title, and URL."""
    if url and title:
        return f"[{index}] [{title}]({url})"
    if url:
        return f"[{index}] [{url}]({url})"
    if title:
        return f"[{index}] {title}"
    return f"[{index}] unknown source"


def _resolve_chunk(
    index: int,
    doc: Document,
    *,
    max_full_doc_chars: int,
    seen_full_doc_ids: set[str],
    full_doc_count: int,
    max_full_docs: int,
    kb_name: str,
) -> tuple[ContextItem | None, int]:
    """Convert one Qdrant result into a ContextItem.

    Handles three retrieval scenarios:
    - full_doc  : load and truncate the original file from disk
    - code_mixed: restore original source code from metadata
    - text/other: use the indexed page_content directly

    Returns ``(item, updated_full_doc_count)``.  Returns ``(None, count)``
    when the doc should be skipped (duplicate full_doc, missing file_path, etc.).
    """
    meta = doc.metadata or {}
    retrieval_mode = meta.get(META_RETRIEVAL_MODE, DEFAULT_RETRIEVAL_MODE)
    title = (
        meta.get(META_TITLE) or meta.get(META_FILE_NAME) or meta.get(META_SOURCE, "")
    )
    url = meta.get(META_URL, "")
    source_label = _build_source_label(index, title, url)

    if retrieval_mode == RETRIEVAL_MODE_FULL_DOC:
        doc_id = meta.get(META_DOC_ID, "")

        if doc_id in seen_full_doc_ids:
            return None, full_doc_count
        if full_doc_count >= max_full_docs:
            return None, full_doc_count

        file_path = meta.get(META_FILE_PATH, "")
        if not file_path:
            logger.warning(
                "full_doc_missing_file_path",
                {"doc_id": doc_id, "kb_name": kb_name},
            )
            return None, full_doc_count

        try:
            full_text = _load_full_text(file_path)
        except Exception as exc:
            logger.warning(
                "full_doc_load_failed",
                {"doc_id": doc_id, "file_path": file_path, "error": str(exc)},
            )
            return None, full_doc_count

        if len(full_text) > max_full_doc_chars:
            full_text = full_text[:max_full_doc_chars]

        seen_full_doc_ids.add(doc_id)
        return (
            ContextItem(
                index=index,
                chunk_type="full_doc",
                content=full_text,
                title=title,
                url=url,
                source_label=source_label,
            ),
            full_doc_count + 1,
        )

    # Chunk retrieval modes — restore original content when available
    chunk_type = meta.get(META_CHUNK_TYPE, "text")
    if chunk_type == CHUNK_TYPE_CODE_MIXED and META_ORIGINAL_CONTENT in meta:
        content = meta[META_ORIGINAL_CONTENT]
        resolved_type: str = "code"
    elif chunk_type == CHUNK_TYPE_IMAGE:
        # Step 1: image chunks fall through as text (caption in page_content).
        # image_url is recorded for Step 2 multimodal assembly.
        return (
            ContextItem(
                index=index,
                chunk_type="image",
                content=doc.page_content,
                image_url=meta.get(META_IMAGE_URL),
                title=title,
                url=url,
                source_label=source_label,
            ),
            full_doc_count,
        )
    else:
        content = doc.page_content
        resolved_type = "text"

    return (
        ContextItem(
            index=index,
            chunk_type=resolved_type,  # type: ignore[arg-type]
            content=content,
            title=title,
            url=url,
            source_label=source_label,
        ),
        full_doc_count,
    )


def _build_context_string(items: list[ContextItem]) -> str:
    """Flatten ContextItems to the numbered text block expected by the RAG prompt."""
    return "\n\n".join(f"[{it.index}] {it.content}" for it in items)


def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant documents from Qdrant based on the user query.

    Workflow:
    - Qdrant similarity search with scores (topK configured via settings)
    - Greedy selection:
        - chunk docs: always included
        - full_doc docs: deduped by doc_id, capped at max_full_docs; full text
          loaded from disk and truncated to max_full_doc_chars
    - Returns structured ``context_items`` list and a flat ``context`` string
      (compatibility shim) plus ``sources`` for citation.
    """
    query = state["query"]
    kb_name = state["kb_name"]

    try:
        emb = get_embedding_for_kb(kb_name)
        store = get_vector_store_for_kb(kb_name, embeddings=emb)
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

    context_items: list[ContextItem] = []
    retrieved_docs = []
    seen_full_doc_ids: set[str] = set()
    full_doc_count = 0

    for i, (doc, _score) in enumerate(results, 1):
        item, full_doc_count = _resolve_chunk(
            index=i,
            doc=doc,
            max_full_doc_chars=max_full_doc_chars,
            seen_full_doc_ids=seen_full_doc_ids,
            full_doc_count=full_doc_count,
            max_full_docs=max_full_docs,
            kb_name=kb_name,
        )
        if item is not None:
            context_items.append(item)
            retrieved_docs.append(doc)

    # Re-index so citation numbers are contiguous after skipped docs
    for pos, item in enumerate(context_items, 1):
        if item.index != pos:
            item.index = pos
            item.source_label = _build_source_label(pos, item.title, item.url)

    return {
        "retrieved_docs": retrieved_docs,
        "context_items": context_items,
        # Compatibility shim: flat string for stream_generate and rag_graph
        "context": _build_context_string(context_items),
        "sources": [it.source_label for it in context_items],
    }


def generate_node(state: RAGState) -> dict:
    """Generate an answer using the LLM with retrieved context and conversation history.

    The caller injects the full prior history via state["messages"]. This node
    appends the current HumanMessage and invokes the LLM, then returns only the
    generated answer. Persistence is handled upstream by the chat router.

    Step 1: uses the flat ``context`` string; image chunks are treated as text
    (their captions are included in the context block).  Step 2 will assemble
    multimodal message content using ``context_items`` directly.
    """
    try:
        llm = get_llm()
        chain = rag_prompt | llm

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
