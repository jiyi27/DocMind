"""Admin runtime settings management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from docmind.api.dependencies import require_super_admin
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.core.llm import clear_llm_cache
from docmind.core.runtime_settings import (
    INGESTION_IMAGE_VISION_API_KEY_KEY,
    INGESTION_IMAGE_VISION_BASE_URL_KEY,
    INGESTION_IMAGE_VISION_MODEL_KEY,
    LLM_API_KEY_KEY,
    LLM_BASE_URL_KEY,
    LLM_MODEL_KEY,
    QDRANT_URL_KEY,
)
from docmind.services.system_settings import (
    get_runtime_settings_payload,
    reload_runtime_settings_cache,
    update_runtime_settings,
)
from docmind.vectorstore.qdrant_store import reset_store_cache

router = APIRouter(prefix="/admin/settings", tags=["admin-settings"])


OptionalNonNegativeInt = Annotated[int | None, Field(ge=0)]
OptionalPositiveInt = Annotated[int | None, Field(gt=0)]


class QdrantSettingsUpdateRequest(BaseModel):
    url: str | None = None


class LLMSettingsUpdateRequest(BaseModel):
    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None


class IngestionSettingsUpdateRequest(BaseModel):
    chunk_size: OptionalPositiveInt = None
    chunk_overlap: OptionalNonNegativeInt = None
    enable_code_summarization: bool | None = None
    image_processor: str | None = None
    image_vision_api_key: str | None = None
    image_vision_model: str | None = None
    image_vision_base_url: str | None = None


class ChatSettingsUpdateRequest(BaseModel):
    max_messages: OptionalNonNegativeInt = None


class RetrievalSettingsUpdateRequest(BaseModel):
    top_k: OptionalPositiveInt = None
    max_full_docs: OptionalPositiveInt = None
    max_full_doc_chars: OptionalPositiveInt = None


class ConfluenceSettingsUpdateRequest(BaseModel):
    base_url: str | None = None
    pat: str | None = None


class RuntimeSettingsUpdateRequest(BaseModel):
    qdrant: QdrantSettingsUpdateRequest | None = None
    llm: LLMSettingsUpdateRequest | None = None
    ingestion: IngestionSettingsUpdateRequest | None = None
    chat: ChatSettingsUpdateRequest | None = None
    retrieval: RetrievalSettingsUpdateRequest | None = None
    confluence: ConfluenceSettingsUpdateRequest | None = None


@router.get("", summary="Get Runtime System Settings")
async def get_runtime_settings(
    _: UserContext = Depends(require_super_admin),
):
    return ok(await get_runtime_settings_payload())


@router.put("", summary="Update Runtime System Settings")
async def put_runtime_settings(
    request: RuntimeSettingsUpdateRequest,
    _: UserContext = Depends(require_super_admin),
):
    payload = request.model_dump(exclude_unset=True)
    qdrant = payload.get("qdrant") or {}
    llm = payload.get("llm") or {}
    ingestion = payload.get("ingestion") or {}
    chat = payload.get("chat") or {}
    retrieval = payload.get("retrieval") or {}
    confluence = payload.get("confluence") or {}

    changed_keys = await update_runtime_settings(
        qdrant_url=qdrant.get("url"),
        llm_base_url=llm.get("base_url"),
        llm_api_key=llm.get("api_key"),
        llm_model=llm.get("model"),
        ingestion_chunk_size=ingestion.get("chunk_size"),
        ingestion_chunk_overlap=ingestion.get("chunk_overlap"),
        ingestion_enable_code_summarization=ingestion.get("enable_code_summarization"),
        ingestion_image_processor=ingestion.get("image_processor"),
        ingestion_image_vision_api_key=ingestion.get("image_vision_api_key"),
        ingestion_image_vision_model=ingestion.get("image_vision_model"),
        ingestion_image_vision_base_url=ingestion.get("image_vision_base_url"),
        chat_max_messages=chat.get("max_messages"),
        retrieval_top_k=retrieval.get("top_k"),
        retrieval_max_full_docs=retrieval.get("max_full_docs"),
        retrieval_max_full_doc_chars=retrieval.get("max_full_doc_chars"),
        confluence_base_url=confluence.get("base_url"),
        confluence_pat=confluence.get("pat"),
    )

    if changed_keys:
        reload_runtime_settings_cache()

    if any(
        key in changed_keys
        for key in (LLM_BASE_URL_KEY, LLM_API_KEY_KEY, LLM_MODEL_KEY)
    ) or any(
        key in changed_keys
        for key in (
            INGESTION_IMAGE_VISION_API_KEY_KEY,
            INGESTION_IMAGE_VISION_MODEL_KEY,
            INGESTION_IMAGE_VISION_BASE_URL_KEY,
        )
    ):
        clear_llm_cache()

    if QDRANT_URL_KEY in changed_keys:
        reset_store_cache()

    return ok(await get_runtime_settings_payload())
