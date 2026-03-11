"""Chat router — RAG conversation endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from docmind.api.schemas import ChatRequest, ChatResponse
from docmind.retrieval.graph import rag_graph

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a question to the RAG knowledge base.

    Supports multi-turn conversation via session_id.
    Mirrors the n8n Webhook → RequestField → Qdrant → AI Agent flow.
    """
    result = rag_graph.invoke(
        {"query": request.chat_input},
        config={"configurable": {"thread_id": request.session_id}},
    )

    return ChatResponse(
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        session_id=request.session_id,
    )
