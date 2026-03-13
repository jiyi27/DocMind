"""Chat router — RAG conversation endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from docmind.api.dependencies import get_current_user
from docmind.api.schemas import ChatRequest
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.retrieval.graph import rag_graph

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("")
async def chat(
    request: ChatRequest,
    current_user: UserContext = Depends(get_current_user),
) -> JSONResponse:
    """Send a question to the RAG knowledge base.

    Retrieval is scoped to the current user's knowledge base (kb_name from JWT).
    Supports multi-turn conversation via session_id.
    """
    result = rag_graph.invoke(
        {
            "query": request.chat_input,
            "kb_name": current_user.kb_name,
        },
        config={"configurable": {"thread_id": request.session_id}},
    )
    return ok({
        "answer": result.get("answer", ""),
        "sources": result.get("sources", []),
        "session_id": request.session_id,
        "kb_name": current_user.kb_name,
    })
