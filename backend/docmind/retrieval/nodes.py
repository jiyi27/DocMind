"""RAG chat graph nodes — retrieve and generate."""

from __future__ import annotations

from typing import AsyncGenerator

from langchain_core.messages import AnyMessage, HumanMessage

from docmind.core import logger
from docmind.core.config import settings
from docmind.core.llm import get_llm
from docmind.retrieval.context import ContextItem
from docmind.retrieval.prompts import rag_prompt
from docmind.retrieval.resolvers import (
    FullDocResolver,
    ResolveAction,
    _build_source_label,
    get_resolver,
)
from docmind.retrieval.state import RAGState
from docmind.core.embedding import get_embedding_for_kb
from docmind.vectorstore.qdrant_store import get_vector_store_for_kb


def _build_context_string(items: list[ContextItem]) -> str:
    """Flatten ContextItems to the numbered text block expected by the RAG prompt."""
    return "\n\n".join(f"[{it.index}] {it.content}" for it in items)


def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant documents from Qdrant based on the user query.

    Traversal semantics:
    - Qdrant returns candidates ranked by similarity (highest first).
    - Regular chunks (text / code / image) are always included.
    - Full-doc chunks are deduped by doc_id and capped at max_full_docs.
      When the cap is hit, traversal stops immediately — results ranked below
      the capped entry are less relevant, so continuing would substitute a
      lower-quality result in its place.
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
    # Tracks which full documents have been loaded to prevent duplicates.
    seen_full_doc_ids: set[str] = set()
    # Counts successfully loaded full documents against the per-request cap.
    full_doc_count = 0

    for i, (doc, _score) in enumerate(results, 1):
        resolver = get_resolver(doc.metadata or {})

        if isinstance(resolver, FullDocResolver):
            result = resolver.resolve(
                i,
                doc,
                max_full_doc_chars=max_full_doc_chars,
                seen_full_doc_ids=seen_full_doc_ids,
                full_doc_count=full_doc_count,
                max_full_docs=max_full_docs,
                kb_name=kb_name,
            )
        else:
            result = resolver.resolve(i, doc)

        if result.action == ResolveAction.STOP:
            # Full-doc cap reached: halt traversal to preserve relevance ordering.
            # Do not fall through to lower-ranked results to fill the slot.
            break

        if result.action == ResolveAction.INCLUDE:
            context_items.append(result.item)
            retrieved_docs.append(doc)
            if isinstance(resolver, FullDocResolver):
                full_doc_count += 1

        # SKIP: resolver declined this result (duplicate / load error); continue.

    # Re-index so citation numbers are contiguous after any skipped docs.
    for pos, item in enumerate(context_items, 1):
        if item.index != pos:
            item.index = pos
            item.source_label = _build_source_label(pos, item.title, item.url)

    return {
        "retrieved_docs": retrieved_docs,
        "context_items": context_items,
        # Compatibility shim: flat string for stream_generate and rag_graph.
        "context": _build_context_string(context_items),
        "sources": [it.source_label for it in context_items],
    }


def generate_node(state: RAGState) -> dict:
    """Generate an answer using the LLM with retrieved context and conversation history.

    The caller injects the full prior history via state["messages"]. This node
    appends the current HumanMessage and invokes the LLM, then returns only the
    generated answer. Persistence is handled upstream by the chat router.

    Generation currently uses the flat ``context`` string only. Image chunks are
    already represented by their summarized/OCR text in that context block.
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
