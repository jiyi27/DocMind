"""Ingestion LangGraph — load → split → embed & store."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from docmind.ingestion.nodes import (
    embed_and_store_node,
    load_document_node,
    split_text_node,
    summarize_code_node,
    summarize_image_node,
)
from docmind.ingestion.state import IngestionState


def build_ingestion_graph():
    """Build and compile the ingestion pipeline graph.

    Flow
    ----
    load_document → split_text → summarize_code → summarize_image → embed_and_store → END
    """
    graph = StateGraph(IngestionState)

    graph.add_node("load_document", load_document_node)
    graph.add_node("split_text", split_text_node)
    graph.add_node("summarize_code", summarize_code_node)
    graph.add_node("summarize_image", summarize_image_node)
    graph.add_node("embed_and_store", embed_and_store_node)

    graph.set_entry_point("load_document")
    graph.add_edge("load_document", "split_text")
    graph.add_edge("split_text", "summarize_code")
    graph.add_edge("summarize_code", "summarize_image")
    graph.add_edge("summarize_image", "embed_and_store")
    graph.add_edge("embed_and_store", END)

    return graph.compile()


# Pre-built graph instance — import and invoke directly
ingestion_graph = build_ingestion_graph()
