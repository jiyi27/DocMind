"""OpenAI-compatible chat completions API."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from docmind.api.dependencies import resolve_user_from_api_key
from docmind.api.response import err_message
from docmind.auth.schemas import UserContext
from docmind.core import logger
from docmind.services.chat_execution import (
    prepare_rag_stream,
    run_rag_completion,
    stream_rag_completion,
)
from docmind.services.system_settings import get_llm_runtime_settings

router = APIRouter(prefix="/api/v1", tags=["openai-compat"])


class OpenAIChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str | list[dict[str, Any]]


class OpenAIChatCompletionsRequest(BaseModel):
    model: str = Field(min_length=1)
    messages: list[OpenAIChatMessage] = Field(min_length=1)
    stream: bool = False


def _openai_error_response(
    *,
    message: str,
    status_code: int,
    error_type: str,
    code: str | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "message": message,
                "type": error_type,
                "param": None,
                "code": code,
            }
        },
    )


async def _authenticate_request(request: Request) -> UserContext:
    authorization = request.headers.get("authorization", "").strip()
    if not authorization:
        raise HTTPException(status_code=401, detail="API key is required")

    scheme, _, raw_api_key = authorization.partition(" ")
    if scheme.lower() != "bearer" or not raw_api_key.strip():
        raise HTTPException(status_code=401, detail="API key is required")

    return await resolve_user_from_api_key(raw_api_key.strip())


def _message_text(message: OpenAIChatMessage) -> str:
    if isinstance(message.content, str):
        return message.content.strip()

    parts: list[str] = []
    for item in message.content:
        if item.get("type") == "text":
            text = str(item.get("text", "")).strip()
            if text:
                parts.append(text)
    return "\n".join(parts).strip()


def _build_langchain_history(
    messages: list[OpenAIChatMessage],
) -> tuple[str, list[HumanMessage | AIMessage | SystemMessage]]:
    """Use the last user message as the active query and earlier turns as history."""
    last_user_index = -1
    for index, message in enumerate(messages):
        if message.role == "user":
            last_user_index = index

    if last_user_index < 0:
        raise ValueError("At least one user message is required")

    query = _message_text(messages[last_user_index])
    if not query:
        raise ValueError("The last user message must include text content")

    history: list[HumanMessage | AIMessage | SystemMessage] = []
    for message in messages[:last_user_index]:
        content = _message_text(message)
        if not content:
            continue
        if message.role == "system":
            history.append(SystemMessage(content=content))
        elif message.role == "assistant":
            history.append(AIMessage(content=content))
        else:
            history.append(HumanMessage(content=content))

    return query, history


def _completion_response(
    *,
    completion_id: str,
    created: int,
    model: str,
    answer: str,
    citations: list[dict[str, int | str]],
) -> JSONResponse:
    # ``citations`` is structured retrieval metadata returned alongside the
    # assistant text so clients can render sources without parsing the answer.
    return JSONResponse(
        status_code=200,
        content={
            "id": completion_id,
            "object": "chat.completion",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            },
            "citations": citations,
        },
    )


def _chunk_payload(
    *,
    completion_id: str,
    created: int,
    model: str,
    delta: dict[str, Any],
    finish_reason: str | None = None,
    citations: list[dict[str, int | str]] | None = None,
) -> str:
    # Streaming sends citations once on the initial chunk; later chunks only
    # carry incremental answer text.
    payload: dict[str, Any] = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    if citations is not None:
        payload["citations"] = citations
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _list_models_response(request: Request) -> JSONResponse:
    try:
        await _authenticate_request(request)
        runtime_model = get_llm_runtime_settings().model
    except HTTPException as exc:
        return _openai_error_response(
            message=str(exc.detail),
            status_code=exc.status_code,
            error_type="invalid_request_error"
            if exc.status_code == 400
            else "authentication_error",
        )

    return JSONResponse(
        status_code=200,
        content={
            "data": [
                {
                    "id": runtime_model,
                    "name": runtime_model,
                }
            ]
        },
    )


@router.get("/models", summary="OpenAI-Compatible Models")
async def list_models(request: Request):
    return await _list_models_response(request)


@router.post("/chat/completions", summary="OpenAI-Compatible Chat Completions")
async def chat_completions(
    body: OpenAIChatCompletionsRequest,
    request: Request,
):
    """OpenAI-style chat endpoint backed by DocMind retrieval.

    The response keeps the standard ``choices`` envelope and adds a top-level
    ``citations`` field containing structured source metadata.
    """
    try:
        current_user = await _authenticate_request(request)
    except HTTPException as exc:
        return _openai_error_response(
            message=str(exc.detail),
            status_code=exc.status_code,
            error_type="invalid_request_error"
            if exc.status_code == 400
            else "authentication_error",
        )

    try:
        query, history = _build_langchain_history(body.messages)
    except ValueError as exc:
        return _openai_error_response(
            message=str(exc),
            status_code=400,
            error_type="invalid_request_error",
        )

    runtime_model = get_llm_runtime_settings().model
    completion_id = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    if not body.stream:
        try:
            result = await run_rag_completion(
                query=query,
                kb_name=current_user.kb_name,
                history=history,
            )
        except Exception as exc:
            logger.error(
                "openai_compat_completion_failed",
                {
                    "kb_name": current_user.kb_name,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                exc=exc,
            )
            return _openai_error_response(
                message=err_message(exc),
                status_code=500,
                error_type="server_error",
            )

        return _completion_response(
            completion_id=completion_id,
            created=created,
            model=runtime_model,
            answer=result.answer,
            citations=result.citations,
        )

    async def event_generator():
        try:
            prepared = await prepare_rag_stream(
                query=query,
                kb_name=current_user.kb_name,
            )

            yield _chunk_payload(
                completion_id=completion_id,
                created=created,
                model=runtime_model,
                delta={"role": "assistant"},
                citations=prepared.citations,
            )

            async for text in stream_rag_completion(
                query=query,
                prepared=prepared,
                history=history,
            ):
                yield _chunk_payload(
                    completion_id=completion_id,
                    created=created,
                    model=runtime_model,
                    delta={"content": text},
                )

            yield _chunk_payload(
                completion_id=completion_id,
                created=created,
                model=runtime_model,
                delta={},
                finish_reason="stop",
            )
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error(
                "openai_compat_stream_failed",
                {
                    "kb_name": current_user.kb_name,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                exc=exc,
            )
            payload = {
                "error": {
                    "message": err_message(exc),
                    "type": "server_error",
                    "param": None,
                    "code": None,
                }
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
