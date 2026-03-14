"""Chat router — RAG conversation endpoint."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage

from docmind.api.dependencies import get_current_user
from docmind.api.schemas import ChatRequest
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.core import logger
from docmind.db.database import get_db
from docmind.db.repositories import ChatMessageRepository, ChatSessionRepository
from docmind.retrieval.graph import rag_graph

router = APIRouter(prefix="/chat", tags=["chat"])


def _build_lc_history(messages: list) -> list:
    """Convert HistoryMessage list (user/assistant) to LangChain message objects."""
    lc_messages = []
    for msg in messages:
        if msg.role == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        else:
            lc_messages.append(AIMessage(content=msg.content))
    return lc_messages


@router.post("", summary="KB Conversation")
async def chat(
    request: ChatRequest,
    current_user: UserContext = Depends(get_current_user),
) -> JSONResponse:
    """Send a question to the RAG pipeline and persist both turns to SQLite.

    The client is responsible for carrying the full conversation history and
    passing it on every request. The server is stateless with respect to
    session memory — no LangGraph checkpointer is used.

    Flow
    ----
    1. Convert client history (user/assistant) → LangChain messages
    2. Invoke the stateless RAG graph with injected history
    3. Persist the user message and assistant answer to SQLite
    4. Return the answer and sources
    """
    # 1. Convert client history to LangChain message objects
    lc_history = _build_lc_history(request.messages)

    # 2. Invoke the stateless RAG graph
    result = rag_graph.invoke(
        {
            "query": request.chat_input,
            "kb_name": current_user.kb_name,
            "messages": lc_history,
        }
    )

    answer = result.get("answer", "")
    sources: list[str] = result.get("sources", [])

    # 3. Persist both turns to SQLite
    async with get_db() as db:
        session_repo = ChatSessionRepository(db)
        message_repo = ChatMessageRepository(db)

        # Ensure the session exists — create it on-the-fly if this is the first turn
        session = await session_repo.get_by_id(request.session_id)
        if not session:
            # Use the first 80 chars of the user's question as the session title
            title = request.chat_input[:80]
            await session_repo.create(
                user_id=current_user.user_id,
                title=title,
                kb_id=current_user.kb_id,
                session_id=request.session_id,
            )
            logger.info("chat_session_created", {"session_id": request.session_id})

        # Write user message
        await message_repo.create(
            session_id=request.session_id,
            role="user",
            content=request.chat_input,
        )

        # Write assistant message (with sources serialised as JSON)
        await message_repo.create(
            session_id=request.session_id,
            role="assistant",
            content=answer,
            sources_json=json.dumps(sources, ensure_ascii=False),
        )

        # Update session activity counters and preview
        await session_repo.touch(
            request.session_id,
            message_count_delta=2,
            last_message_preview=answer[:160],
        )

    return ok(
        {
            "answer": answer,
            "sources": sources,
            "session_id": request.session_id,
            "kb_name": current_user.kb_name,
        }
    )
