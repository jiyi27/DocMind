"""Chat router — RAG conversation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from docmind.api.schemas import ChatRequest, ChatResponse
from docmind.core import logger
from docmind.retrieval.graph import rag_graph

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a question to the RAG knowledge base.

    Supports multi-turn conversation via session_id.
    """
    try:
        result = rag_graph.invoke(
            {"query": request.chat_input},
            config={"configurable": {"thread_id": request.session_id}},
        )
    except Exception as exc:
        logger.error("chat_failed", {
            "session_id": request.session_id,
            "query_length": len(request.chat_input),
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise HTTPException(
            status_code=500,
            detail="Failed to process your request. Please try again later.",
        ) from exc

    return ChatResponse(
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
        session_id=request.session_id,
    )
