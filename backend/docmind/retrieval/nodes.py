"""RAG chat graph nodes — retrieve and generate."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

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

        # Append current turn to the injected history before invoking the LLM
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
