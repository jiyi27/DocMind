"""RAG chat LangGraph — retrieve → generate."""

from __future__ import annotations

from langgraph.graph import END, StateGraph
from langgraph.checkpoint.memory import MemorySaver

from docmind.retrieval.nodes import generate_node, retrieve_node
from docmind.retrieval.state import RAGState


def build_rag_graph(checkpointer=None):
    """Build and compile the RAG chat graph.

    Flow
    ----
    retrieve → generate → END

    Parameters
    ----------
    checkpointer:
        Optional LangGraph checkpointer for session persistence.
        Defaults to in-memory MemorySaver. For production, swap to
        SqliteSaver or PostgresSaver.
    """
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    if checkpointer is None:
        checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)


# Pre-built graph instance with in-memory sessions
rag_graph = build_rag_graph()
