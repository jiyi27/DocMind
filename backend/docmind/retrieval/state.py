"""RAG chat state definition."""

from __future__ import annotations

from typing import Required, TypedDict

from langchain_core.messages import AnyMessage

from docmind.retrieval.context import ContextItem


class RAGState(TypedDict, total=False):
    """State flowing through the RAG chat graph.

    Stateless design: the caller injects the full conversation history on
    every invocation. No LangGraph checkpointer is involved; persistence
    is delegated to the chat router (SQLite via ChatMessageRepository).

    Attributes
    ----------
    query : str
        The user's current question (required).
    kb_name : str
        Knowledge base slug — selects the Qdrant collection to search (required).
    retrieved_docs : list
        Raw documents retrieved from the vector store.
    context_items : list[ContextItem]
        Structured retrieval results, one per retrieved chunk.  The generate
        node assembles the LLM message from this list rather than from the
        flat ``context`` string.
    context : str
        Compatibility shim: flat text context derived from ``context_items``.
        Kept so that ``stream_generate`` (which accepts a plain string) does
        not require a signature change in Step 1.
    citations : list[dict[str, int | str]]
        Structured citation metadata derived from ``context_items``.
    messages : list[AnyMessage]
        Full conversation history (prior turns) injected by the caller.
        The generate node appends the current HumanMessage before invoking
        the LLM, but does NOT mutate this field in the returned state.
    answer : str
        The final generated answer.
    """

    # Required fields — must be provided by the caller on every invocation
    query: Required[str]
    kb_name: Required[str]

    # Optional fields populated by graph nodes
    retrieved_docs: list
    context_items: list[ContextItem]
    context: str  # compatibility shim derived from context_items
    citations: list[dict[str, int | str]]
    messages: list[AnyMessage]
    answer: str
