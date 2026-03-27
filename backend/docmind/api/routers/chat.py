"""Chat router — RAG conversation endpoint (blocking + streaming)."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from docmind.api.dependencies import get_current_user
from docmind.api.schemas import ChatRequest
from docmind.api.response import err_message, ok
from docmind.auth.schemas import UserContext
from docmind.core import logger
from docmind.db.database import get_db
from docmind.db.repositories import ChatMessageRepository, ChatSessionRepository
from docmind.retrieval.title import generate_session_title
from docmind.services.chat_execution import (
    db_messages_to_langchain,
    prepare_rag_stream,
    run_rag_completion,
    stream_rag_completion,
)
from docmind.services.system_settings import get_chat_max_messages

router = APIRouter(prefix="/chat", tags=["chat"])


def _sse_event(payload: dict) -> str:
    """Serialize a payload as a single SSE data event."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


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
        max_msg = get_chat_max_messages()
        all_rows = await message_repo.list_by_session(request.session_id)
        prior_rows = all_rows[-max_msg:] if max_msg > 0 else all_rows

    # 2. Convert to LangChain messages and invoke RAG graph (outside DB context)
    lc_history = db_messages_to_langchain(prior_rows)
    result = await run_rag_completion(
        query=request.chat_input,
        kb_name=current_user.kb_name,
        history=lc_history,
    )

    answer = result.answer
    sources = result.sources

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


@router.post("/stream", summary="KB Conversation (Streaming SSE)")
async def chat_stream(
    request: ChatRequest,
    current_user: UserContext = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the RAG answer token-by-token via Server-Sent Events.

    SSE event types
    ---------------
    - ``data: {"type": "sources", "sources": [...]}``    — sent first, before text
    - ``data: {"type": "chunk",   "text": "..."}``       — one per LLM token chunk
    - ``data: {"type": "done",    "session_id": "..."}`` — sent after final token
    - ``data: {"type": "error",   "message": "..."}``    — on unexpected failure

    Flow
    ----
    1. Load session + history from SQLite
    2. Run retrieval (sync) to get context + sources
    3. Immediately persist the user message to SQLite
    4. Emit a ``sources`` event, then stream LLM chunks via SSE
    5. After stream ends, persist the full assistant answer and trigger title
    """

    async def event_generator():
        try:
            # ── 1. Load session and history ──────────────────────────────────
            async with get_db() as db:
                session_repo = ChatSessionRepository(db)
                message_repo = ChatMessageRepository(db)

                session = await session_repo.get_by_id(request.session_id)
                if not session:
                    session = await session_repo.create(
                        user_id=current_user.user_id,
                        title="New Conversation",
                        kb_id=current_user.kb_id,
                        session_id=request.session_id,
                    )
                    logger.info(
                        "chat_session_created", {"session_id": request.session_id}
                    )

                is_first_turn = session.get("message_count", 0) == 0

                max_msg = get_chat_max_messages()
                all_rows = await message_repo.list_by_session(request.session_id)
                prior_rows = all_rows[-max_msg:] if max_msg > 0 else all_rows

            lc_history = db_messages_to_langchain(prior_rows)

            # ── 2. Retrieval (sync Qdrant IO — offload to thread pool) ──────────
            prepared = await prepare_rag_stream(
                query=request.chat_input,
                kb_name=current_user.kb_name,
            )

            # ── 3. Persist user message immediately ──────────────────────────
            async with get_db() as db:
                message_repo = ChatMessageRepository(db)
                await message_repo.create(
                    session_id=request.session_id,
                    role="user",
                    content=request.chat_input,
                )

            # ── Emit sources before text starts ──────────────────────────────
            yield _sse_event({"type": "sources", "sources": prepared.sources})

            # ── 4. Stream LLM generation ─────────────────────────────────────
            answer_parts: list[str] = []
            async for text in stream_rag_completion(
                query=request.chat_input,
                prepared=prepared,
                history=lc_history,
            ):
                answer_parts.append(text)
                yield _sse_event({"type": "chunk", "text": text})

            # ── 5. Persist assistant answer + update session ─────────────────
            full_answer = "".join(answer_parts)
            async with get_db() as db:
                session_repo = ChatSessionRepository(db)
                message_repo = ChatMessageRepository(db)

                await message_repo.create(
                    session_id=request.session_id,
                    role="assistant",
                    content=full_answer,
                    sources_json=json.dumps(prepared.sources, ensure_ascii=False),
                )
                await session_repo.touch(
                    request.session_id,
                    message_count_delta=2,
                    last_message_preview=full_answer[:160],
                )

            # Fire-and-forget title generation on first turn
            if is_first_turn:
                asyncio.create_task(
                    generate_session_title(
                        session_id=request.session_id,
                        user_input=request.chat_input,
                        assistant_answer=full_answer,
                    )
                )

            # ── Done event ────────────────────────────────────────────────────
            yield _sse_event({"type": "done", "session_id": request.session_id})
        except Exception as exc:
            log = logger.warning if hasattr(exc, "message") else logger.error
            log(
                "chat_stream_exception",
                {
                    "session_id": request.session_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                exc=exc,
            )
            yield _sse_event({"type": "error", "message": err_message(exc)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable Nginx buffering if present
        },
    )
