"""Chat router — RAG conversation endpoint."""

from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from langchain_core.messages import AIMessage, HumanMessage

from docmind.api.dependencies import get_current_user
from docmind.api.schemas import ChatRequest
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.core import logger
from docmind.core.config import settings
from docmind.db.database import get_db
from docmind.db.repositories import ChatMessageRepository, ChatSessionRepository
from docmind.retrieval.graph import rag_graph
from docmind.retrieval.title import generate_session_title

router = APIRouter(prefix="/chat", tags=["chat"])


def _db_messages_to_lc(rows: list[dict]) -> list:
    """Convert DB message rows (dicts with role/content) to LangChain message objects."""
    result = []
    for row in rows:
        if row["role"] == "user":
            result.append(HumanMessage(content=row["content"]))
        else:
            result.append(AIMessage(content=row["content"]))
    return result


@router.post("", summary="KB Conversation")
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    current_user: UserContext = Depends(get_current_user),
) -> JSONResponse:
    """Send a question to the RAG pipeline and persist both turns to SQLite.

    History is loaded from the database on every request — the client no longer
    needs to carry or transmit conversation history.

    Flow
    ----
    1. Load existing message history from SQLite (truncated to MAX_MESSAGES)
    2. Convert DB rows → LangChain messages and invoke the RAG graph
    3. Persist the new user message and assistant answer to SQLite
    4. If this is the first turn, schedule async LLM title generation
    5. Return the answer and sources
    """
    async with get_db() as db:
        session_repo = ChatSessionRepository(db)
        message_repo = ChatMessageRepository(db)

        # Check session existence and load history in one open connection
        session = await session_repo.get_by_id(request.session_id)

        if not session:
            # Guard against missing session (shouldn't happen — POST /chats creates it first)
            session = await session_repo.create(
                user_id=current_user.user_id,
                title="New Conversation",
                kb_id=current_user.kb_id,
                session_id=request.session_id,
            )
            logger.info("chat_session_created", {"session_id": request.session_id})

        # First turn = session has no messages yet (message_count == 0)
        is_first_turn = session.get("message_count", 0) == 0

        # 1. Load prior messages from DB, keep only the most recent MAX_MESSAGES
        max_msg = settings.retrieval.max_messages
        all_rows = await message_repo.list_by_session(request.session_id)
        prior_rows = all_rows[-max_msg:] if max_msg > 0 else all_rows

    # 2. Convert to LangChain messages and invoke RAG graph (outside DB context)
    lc_history = _db_messages_to_lc(prior_rows)
    result = rag_graph.invoke(
        {
            "query": request.chat_input,
            "kb_name": current_user.kb_name,
            "messages": lc_history,
        }
    )

    answer = result.get("answer", "")
    sources: list[str] = result.get("sources", [])

    # 3. Persist both turns and update session metadata
    async with get_db() as db:
        session_repo = ChatSessionRepository(db)
        message_repo = ChatMessageRepository(db)

        await message_repo.create(
            session_id=request.session_id,
            role="user",
            content=request.chat_input,
        )
        await message_repo.create(
            session_id=request.session_id,
            role="assistant",
            content=answer,
            sources_json=json.dumps(sources, ensure_ascii=False),
        )
        await session_repo.touch(
            request.session_id,
            message_count_delta=2,
            last_message_preview=answer[:160],
        )

    # 4. First turn: schedule title generation to run after the response is sent
    if is_first_turn:
        background_tasks.add_task(
            generate_session_title,
            session_id=request.session_id,
            user_input=request.chat_input,
            assistant_answer=answer,
        )

    return ok(
        {
            "answer": answer,
            "sources": sources,
            "session_id": request.session_id,
            "kb_name": current_user.kb_name,
            "is_first_turn": is_first_turn,
        }
    )
