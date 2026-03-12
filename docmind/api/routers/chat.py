"""Chat router — RAG conversation endpoint."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from docmind.api.schemas import ChatRequest
from docmind.api.response import ok
from docmind.retrieval.graph import rag_graph

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(request: ChatRequest) -> JSONResponse:
    """Send a question to the RAG knowledge base.

    Supports multi-turn conversation via session_id.
    Exceptions bubble up to the global handler in response.py.
    """
    result = rag_graph.invoke(
        {"query": request.chat_input},
        config={"configurable": {"thread_id": request.session_id}},
    )
    return ok({
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "session_id": request.session_id,
    })
