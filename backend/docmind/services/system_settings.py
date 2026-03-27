"""Runtime-editable system settings backed by SQLite and cached in memory."""

from __future__ import annotations

import threading

from docmind.core.exceptions import ConfigError
from docmind.core.runtime_settings import (
    CHAT_MAX_MESSAGES_KEY,
    CONFLUENCE_BASE_URL_KEY,
    CONFLUENCE_PAT_KEY,
    ConfluenceRuntimeSettings,
    INGESTION_CHUNK_OVERLAP_KEY,
    INGESTION_CHUNK_SIZE_KEY,
    INGESTION_ENABLE_CODE_SUMMARIZATION_KEY,
    INGESTION_IMAGE_PROCESSOR_KEY,
    INGESTION_IMAGE_VISION_API_KEY_KEY,
    INGESTION_IMAGE_VISION_BASE_URL_KEY,
    INGESTION_IMAGE_VISION_MODEL_KEY,
    ImageVisionRuntimeSettings,
    LLM_API_KEY_KEY,
    LLM_BASE_URL_KEY,
    LLM_MODEL_KEY,
    LLMRuntimeSettings,
    QDRANT_URL_KEY,
    RETRIEVAL_MAX_FULL_DOC_CHARS_KEY,
    RETRIEVAL_MAX_FULL_DOCS_KEY,
    RETRIEVAL_TOP_K_KEY,
    RUNTIME_SETTING_KEYS,
    RUNTIME_SETTING_SPECS,
    QdrantRuntimeSettings,
    RuntimeSettings,
    build_runtime_settings,
    runtime_settings_to_payload,
    serialize_runtime_value,
)
from docmind.db.database import create_sync_connection, get_db
from docmind.db.repositories import SystemSettingsRepository

_cache_lock = threading.Lock()
_settings_cache: RuntimeSettings | None = None


def _read_runtime_settings_sync() -> RuntimeSettings:
    conn = create_sync_connection()
    try:
        placeholders = ",".join("?" for _ in RUNTIME_SETTING_KEYS)
        query = f"SELECT key, value FROM system_settings WHERE key IN ({placeholders})"
        rows = conn.execute(query, tuple(RUNTIME_SETTING_KEYS)).fetchall()
        values = {str(row["key"]): str(row["value"]) for row in rows}
    finally:
        conn.close()
    return build_runtime_settings(values)


def initialize_runtime_settings_cache() -> RuntimeSettings:
    global _settings_cache
    with _cache_lock:
        _settings_cache = _read_runtime_settings_sync()
        return _settings_cache


def get_runtime_settings() -> RuntimeSettings:
    global _settings_cache

    if _settings_cache is not None:
        return _settings_cache

    with _cache_lock:
        if _settings_cache is None:
            _settings_cache = _read_runtime_settings_sync()
        return _settings_cache


def reload_runtime_settings_cache() -> tuple[RuntimeSettings, RuntimeSettings]:
    global _settings_cache
    with _cache_lock:
        old = _settings_cache or _read_runtime_settings_sync()
        new = _read_runtime_settings_sync()
        _settings_cache = new
        return old, new


def clear_runtime_settings_cache() -> None:
    global _settings_cache
    with _cache_lock:
        _settings_cache = None


def _require_non_empty(value: str, key: str) -> str:
    value = value.strip()
    if not value:
        raise ConfigError(
            f"System setting '{key}' is missing. Please update it in admin settings."
        )
    return value


def _require_image_vision_settings(runtime: RuntimeSettings) -> RuntimeSettings:
    vision = runtime.ingestion.image_vision
    missing_fields: list[str] = []
    if not vision.api_key.strip():
        missing_fields.append(INGESTION_IMAGE_VISION_API_KEY_KEY)
    if not vision.model.strip():
        missing_fields.append(INGESTION_IMAGE_VISION_MODEL_KEY)
    if not vision.base_url.strip():
        missing_fields.append(INGESTION_IMAGE_VISION_BASE_URL_KEY)

    if missing_fields:
        raise ConfigError(
            "Image vision is not fully configured. Missing system settings: "
            + ", ".join(missing_fields)
            + "."
        )
    return runtime


def _validate_runtime_dependencies(runtime: RuntimeSettings) -> None:
    if runtime.ingestion.image_processor == "multimodal":
        _require_image_vision_settings(runtime)
    if bool(runtime.confluence.base_url.strip()) != bool(
        runtime.confluence.pat.strip()
    ):
        raise ConfigError(
            "Confluence is not fully configured. Missing system settings: "
            + ", ".join(
                key
                for key, value in (
                    (CONFLUENCE_BASE_URL_KEY, runtime.confluence.base_url),
                    (CONFLUENCE_PAT_KEY, runtime.confluence.pat),
                )
                if not value.strip()
            )
            + "."
        )


def get_qdrant_runtime_settings() -> QdrantRuntimeSettings:
    runtime = get_runtime_settings()
    _require_non_empty(runtime.qdrant.url, QDRANT_URL_KEY)
    return runtime.qdrant


def get_llm_runtime_settings() -> LLMRuntimeSettings:
    runtime = get_runtime_settings()

    missing_fields: list[str] = []
    if not runtime.llm.base_url.strip():
        missing_fields.append(LLM_BASE_URL_KEY)
    if not runtime.llm.api_key.strip():
        missing_fields.append(LLM_API_KEY_KEY)
    if not runtime.llm.model.strip():
        missing_fields.append(LLM_MODEL_KEY)
    if missing_fields:
        raise ConfigError(
            "LLM is not fully configured. Missing system settings: "
            + ", ".join(missing_fields)
            + "."
        )
    return runtime.llm


def get_image_vision_runtime_settings() -> ImageVisionRuntimeSettings:
    runtime = get_runtime_settings()
    return _require_image_vision_settings(runtime).ingestion.image_vision


def get_confluence_runtime_settings() -> ConfluenceRuntimeSettings:
    runtime = get_runtime_settings()
    if bool(runtime.confluence.base_url.strip()) != bool(
        runtime.confluence.pat.strip()
    ):
        raise ConfigError(
            "Confluence is not fully configured. Missing system settings: "
            + ", ".join(
                key
                for key, value in (
                    (CONFLUENCE_BASE_URL_KEY, runtime.confluence.base_url),
                    (CONFLUENCE_PAT_KEY, runtime.confluence.pat),
                )
                if not value.strip()
            )
            + "."
        )
    if not runtime.confluence.enabled:
        raise ConfigError(
            "Confluence is not configured. Please update it in admin settings."
        )
    return runtime.confluence


def get_chat_max_messages() -> int:
    return get_runtime_settings().chat.max_messages


def get_retrieval_top_k() -> int:
    return get_runtime_settings().retrieval.top_k


async def get_runtime_settings_payload() -> dict[str, dict[str, object]]:
    return runtime_settings_to_payload(get_runtime_settings())


async def update_runtime_settings(
    *,
    qdrant_url: str | None = None,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    ingestion_chunk_size: int | None = None,
    ingestion_chunk_overlap: int | None = None,
    ingestion_enable_code_summarization: bool | None = None,
    ingestion_image_processor: str | None = None,
    ingestion_image_vision_api_key: str | None = None,
    ingestion_image_vision_model: str | None = None,
    ingestion_image_vision_base_url: str | None = None,
    chat_max_messages: int | None = None,
    retrieval_top_k: int | None = None,
    retrieval_max_full_docs: int | None = None,
    retrieval_max_full_doc_chars: int | None = None,
    confluence_base_url: str | None = None,
    confluence_pat: str | None = None,
) -> list[str]:
    current = get_runtime_settings()
    raw_updates: dict[str, object] = {}

    if qdrant_url is not None:
        raw_updates[QDRANT_URL_KEY] = qdrant_url
    if llm_base_url is not None:
        raw_updates[LLM_BASE_URL_KEY] = llm_base_url
    if llm_api_key is not None:
        raw_updates[LLM_API_KEY_KEY] = llm_api_key
    if llm_model is not None:
        raw_updates[LLM_MODEL_KEY] = llm_model
    if ingestion_chunk_size is not None:
        raw_updates[INGESTION_CHUNK_SIZE_KEY] = ingestion_chunk_size
    if ingestion_chunk_overlap is not None:
        raw_updates[INGESTION_CHUNK_OVERLAP_KEY] = ingestion_chunk_overlap
    if ingestion_enable_code_summarization is not None:
        raw_updates[INGESTION_ENABLE_CODE_SUMMARIZATION_KEY] = (
            ingestion_enable_code_summarization
        )
    if ingestion_image_processor is not None:
        raw_updates[INGESTION_IMAGE_PROCESSOR_KEY] = ingestion_image_processor
    if ingestion_image_vision_api_key is not None:
        raw_updates[INGESTION_IMAGE_VISION_API_KEY_KEY] = ingestion_image_vision_api_key
    if ingestion_image_vision_model is not None:
        raw_updates[INGESTION_IMAGE_VISION_MODEL_KEY] = ingestion_image_vision_model
    if ingestion_image_vision_base_url is not None:
        raw_updates[INGESTION_IMAGE_VISION_BASE_URL_KEY] = (
            ingestion_image_vision_base_url
        )
    if chat_max_messages is not None:
        raw_updates[CHAT_MAX_MESSAGES_KEY] = chat_max_messages
    if retrieval_top_k is not None:
        raw_updates[RETRIEVAL_TOP_K_KEY] = retrieval_top_k
    if retrieval_max_full_docs is not None:
        raw_updates[RETRIEVAL_MAX_FULL_DOCS_KEY] = retrieval_max_full_docs
    if retrieval_max_full_doc_chars is not None:
        raw_updates[RETRIEVAL_MAX_FULL_DOC_CHARS_KEY] = retrieval_max_full_doc_chars
    if confluence_base_url is not None:
        raw_updates[CONFLUENCE_BASE_URL_KEY] = confluence_base_url
    if confluence_pat is not None:
        raw_updates[CONFLUENCE_PAT_KEY] = confluence_pat

    previous_values = {
        QDRANT_URL_KEY: current.qdrant.url,
        LLM_BASE_URL_KEY: current.llm.base_url,
        LLM_API_KEY_KEY: current.llm.api_key,
        LLM_MODEL_KEY: current.llm.model,
        INGESTION_CHUNK_SIZE_KEY: str(current.ingestion.chunk_size),
        INGESTION_CHUNK_OVERLAP_KEY: str(current.ingestion.chunk_overlap),
        INGESTION_ENABLE_CODE_SUMMARIZATION_KEY: (
            "true" if current.ingestion.enable_code_summarization else "false"
        ),
        INGESTION_IMAGE_PROCESSOR_KEY: current.ingestion.image_processor,
        INGESTION_IMAGE_VISION_API_KEY_KEY: current.ingestion.image_vision.api_key,
        INGESTION_IMAGE_VISION_MODEL_KEY: current.ingestion.image_vision.model,
        INGESTION_IMAGE_VISION_BASE_URL_KEY: current.ingestion.image_vision.base_url,
        CHAT_MAX_MESSAGES_KEY: str(current.chat.max_messages),
        RETRIEVAL_TOP_K_KEY: str(current.retrieval.top_k),
        RETRIEVAL_MAX_FULL_DOCS_KEY: str(current.retrieval.max_full_docs),
        RETRIEVAL_MAX_FULL_DOC_CHARS_KEY: str(current.retrieval.max_full_doc_chars),
        CONFLUENCE_BASE_URL_KEY: current.confluence.base_url,
        CONFLUENCE_PAT_KEY: current.confluence.pat,
    }
    serialized_updates = {
        key: serialize_runtime_value(RUNTIME_SETTING_SPECS[key], value)
        for key, value in raw_updates.items()
        if value is not None
    }

    candidate_values = {
        **previous_values,
    }
    candidate_values.update(serialized_updates)
    candidate_runtime = build_runtime_settings(candidate_values)
    _validate_runtime_dependencies(candidate_runtime)

    if serialized_updates:
        async with get_db() as db:
            repo = SystemSettingsRepository(db)
            await repo.upsert_many(serialized_updates)

    changed_keys = [
        key
        for key, value in serialized_updates.items()
        if previous_values.get(key) != value
    ]
    return changed_keys
