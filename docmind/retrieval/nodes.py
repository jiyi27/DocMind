"""RAG chat graph nodes — retrieve and generate."""

from __future__ import annotations

from langchain_core.messages import AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from docmind.core.config import settings
from docmind.retrieval.prompts import rag_prompt
from docmind.retrieval.state import RAGState
from docmind.vectorstore.qdrant_store import get_vector_store


def retrieve_node(state: RAGState) -> dict:
    """Retrieve relevant documents from Qdrant based on the user query.

    Mirrors the n8n workflow:
    - Qdrant Vector Store (mode=load, topK=3)
    - Code node that formats context + sources
    """
    query = state["query"]
    store = get_vector_store()
    docs = store.similarity_search(query, k=settings.retrieval.top_k)

    # Build formatted context & sources — same logic as the n8n Code node
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
    """Generate an answer using the LLM with retrieved context.

    Uses OpenRouter-compatible ChatOpenAI, matching the n8n AI Agent node.
    """
    llm = ChatOpenAI(
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
        model=settings.llm.model,
    )

    # Build the prompt with context, sources, and conversation history
    chain = rag_prompt | llm

    # The user's current query is appended to messages
    messages = list(state.get("messages", []))
    messages.append(HumanMessage(content=state["query"]))

    result = chain.invoke({
        "context": state.get("context", ""),
        "sources": "\n".join(state.get("sources", [])),
        "messages": messages,
    })

    return {
        "answer": result.content,
        "messages": [
            HumanMessage(content=state["query"]),
            AIMessage(content=result.content),
        ],
    }
