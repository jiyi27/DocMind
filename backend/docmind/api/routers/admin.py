"""Admin runtime settings management."""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends

from docmind.api.dependencies import require_super_admin
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.core.llm import clear_llm_cache
from docmind.services.system_settings import (
    get_runtime_settings_payload,
    update_runtime_settings,
)

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


class LLMSettingsUpdateRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class ChatSettingsUpdateRequest(BaseModel):
    max_messages: int = Field(ge=0)


class RetrievalSettingsUpdateRequest(BaseModel):
    top_k: int = Field(gt=0)


@router.get("", summary="Get Runtime System Settings")
async def get_runtime_settings(
    _: UserContext = Depends(require_super_admin),
):
    return ok(await get_runtime_settings_payload())


@router.put("/llm", summary="Update Runtime LLM Settings")
async def update_llm_settings(
    request: LLMSettingsUpdateRequest,
    _: UserContext = Depends(require_super_admin),
):
    await update_runtime_settings(
        llm_base_url=request.base_url,
        llm_api_key=request.api_key,
        llm_model=request.model,
    )
    clear_llm_cache()
    return ok(await get_runtime_settings_payload())


@router.put("/chat", summary="Update Runtime Chat Settings")
async def update_chat_settings(
    request: ChatSettingsUpdateRequest,
    _: UserContext = Depends(require_super_admin),
):
    await update_runtime_settings(chat_max_messages=request.max_messages)
    return ok(await get_runtime_settings_payload())


@router.put("/retrieval", summary="Update Runtime Retrieval Settings")
async def update_retrieval_settings(
    request: RetrievalSettingsUpdateRequest,
    _: UserContext = Depends(require_super_admin),
):
    await update_runtime_settings(retrieval_top_k=request.top_k)
    return ok(await get_runtime_settings_payload())
