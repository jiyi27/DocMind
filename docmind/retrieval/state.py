"""RAG chat state definition."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class RAGState(TypedDict, total=False):
    """State flowing through the RAG chat graph.

    Attributes
    ----------
    query : str
        The user's current question.
    session_id : str
        Session identifier for multi-turn conversation tracking.
    retrieved_docs : list
        Raw documents retrieved from the vector store.
    context : str
        Formatted context string assembled from retrieved docs.
    sources : list[str]
        Formatted source references for citation.
    messages : Annotated[list[AnyMessage], add_messages]
        Conversation history managed by LangGraph's add_messages reducer.
        This allows future context management (trimming, summarization)
        without changing the state schema.
    answer : str
        The final generated answer.
    """

    query: str
    session_id: str
    retrieved_docs: list
    context: str
    sources: list[str]
    # Reducer-backed field: LangGraph calls add_messages(old, new) on each state update, 
    # appending new messages instead of overwriting the list.
    messages: Annotated[list[AnyMessage], add_messages]
    answer: str
