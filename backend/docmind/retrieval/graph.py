"""RAG chat LangGraph — retrieve → generate.

Stateless design: conversation history is passed in via the initial state
on every invocation. No checkpointer is used; persistence is handled by
the chat router writing to SQLite after each turn.
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from docmind.retrieval.nodes import generate_node, retrieve_node
from docmind.retrieval.state import RAGState


def build_rag_graph():
    """Build and compile a stateless RAG chat graph.

    Flow
    ----
    retrieve → generate → END

    History is injected into the initial state by the caller; the graph
    itself holds no session state between invocations.
    """
    graph = StateGraph(RAGState)

    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "generate")
    graph.add_edge("generate", END)

    return graph.compile()


# Module-level singleton — safe to reuse across requests (stateless)
rag_graph = build_rag_graph()
