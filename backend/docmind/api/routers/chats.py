"""
Chat history router.

GET  /chats                 - list user chat sessions
GET  /chats/{session_id}    - get session detail with messages
POST /chats                 - create a new chat session
POST /chats/{session_id}/messages - append a message to a session
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status

from docmind.api.dependencies import get_current_user
from docmind.api.response import ok
from docmind.api.schemas import ChatSessionCreate, ChatMessageCreate
from docmind.auth.schemas import UserContext
from docmind.db.database import get_db
from docmind.db.repositories import ChatSessionRepository, ChatMessageRepository

router = APIRouter(prefix="/chats", tags=["chat-history"])


def _parse_sources(raw: str) -> list[str]:
    if not raw:
        return []
    try:
        payload = json.loads(raw)
        return payload if isinstance(payload, list) else []
    except json.JSONDecodeError:
        return []


@router.get("", summary="List chat sessions")
async def list_chat_sessions(
    kb_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    current_user: UserContext = Depends(get_current_user),
):
    """Return a list of chat sessions for the current user."""
    async with get_db() as db:
        repo = ChatSessionRepository(db)
        total = await repo.count_by_user(current_user.user_id, kb_id=kb_id)
        sessions = await repo.list_by_user(
            current_user.user_id,
            kb_id=kb_id,
            limit=limit,
            offset=offset,
        )
    return ok(data={"items": sessions, "total": total, "limit": limit, "offset": offset})


@router.get("/{session_id}", summary="Get chat session detail")
async def get_chat_session(
    session_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Return a chat session and all messages for the current user."""
    async with get_db() as db:
        session_repo = ChatSessionRepository(db)
        message_repo = ChatMessageRepository(db)

        session = await session_repo.get_by_id(session_id)
        if not session or session["user_id"] != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

        messages = await message_repo.list_by_session(session_id)
        for msg in messages:
            msg["sources"] = _parse_sources(msg.pop("sources_json", ""))

    return ok(data={"session": session, "messages": messages})


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create chat session")
async def create_chat_session(
    body: ChatSessionCreate,
    current_user: UserContext = Depends(get_current_user),
):
    """Create a new chat session for the current user."""
    async with get_db() as db:
        repo = ChatSessionRepository(db)
        session = await repo.create(
            user_id=current_user.user_id,
            title=body.title,
            kb_id=body.kb_id or current_user.kb_id,
        )
    return ok(data=session, message="Chat session created")


@router.post("/{session_id}/messages", status_code=status.HTTP_201_CREATED, summary="Append chat message")
async def create_chat_message(
    session_id: str,
    body: ChatMessageCreate,
    current_user: UserContext = Depends(get_current_user),
):
    """Append a message to a chat session owned by the current user."""
    async with get_db() as db:
        session_repo = ChatSessionRepository(db)
        message_repo = ChatMessageRepository(db)

        session = await session_repo.get_by_id(session_id)
        if not session or session["user_id"] != current_user.user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found")

        message = await message_repo.create(
            session_id=session_id,
            role=body.role,
            content=body.content,
            sources_json=json.dumps(body.sources),
            model_name=body.model_name,
            token_count=body.token_count,
        )
        preview = body.content[:160] if body.content else ""
        await session_repo.touch(session_id, message_count_delta=1, last_message_preview=preview)

        message["sources"] = body.sources
        message.pop("sources_json", None)

    return ok(data=message, message="Message created")
