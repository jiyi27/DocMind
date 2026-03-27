"""Runtime-editable system settings backed by SQLite."""

from __future__ import annotations

from dataclasses import dataclass
import threading

from docmind.core.config import settings
from docmind.core.exceptions import ConfigError
from docmind.db.database import create_sync_connection, get_db
from docmind.db.repositories import SystemSettingsRepository

LLM_BASE_URL_KEY = "llm_base_url"
LLM_API_KEY_KEY = "llm_api_key"
LLM_MODEL_KEY = "llm_model"
CHAT_MAX_MESSAGES_KEY = "chat_max_messages"
RETRIEVAL_TOP_K_KEY = "retrieval_top_k"

_RUNTIME_SETTING_KEYS = [
    LLM_BASE_URL_KEY,
    LLM_API_KEY_KEY,
    LLM_MODEL_KEY,
    CHAT_MAX_MESSAGES_KEY,
    RETRIEVAL_TOP_K_KEY,
]
_cache_lock = threading.Lock()
_settings_cache: dict[str, str] | None = None


@dataclass(frozen=True)
class LLMRuntimeSettings:
    base_url: str
    api_key: str
    model: str


def _read_runtime_settings_sync() -> dict[str, str]:
    conn = create_sync_connection()
    try:
        placeholders = ",".join("?" for _ in _RUNTIME_SETTING_KEYS)
        query = f"SELECT key, value FROM system_settings WHERE key IN ({placeholders})"
        rows = conn.execute(query, tuple(_RUNTIME_SETTING_KEYS)).fetchall()
        values = {str(row["key"]): str(row["value"]) for row in rows}
    finally:
        conn.close()

    return {
        LLM_BASE_URL_KEY: values.get(LLM_BASE_URL_KEY, settings.llm.base_url),
        LLM_API_KEY_KEY: values.get(LLM_API_KEY_KEY, settings.llm.api_key),
        LLM_MODEL_KEY: values.get(LLM_MODEL_KEY, settings.llm.model),
        CHAT_MAX_MESSAGES_KEY: values.get(
            CHAT_MAX_MESSAGES_KEY, str(settings.retrieval.max_messages)
        ),
        RETRIEVAL_TOP_K_KEY: values.get(
            RETRIEVAL_TOP_K_KEY, str(settings.retrieval.top_k)
        ),
    }


def _get_cached_runtime_settings() -> dict[str, str]:
    global _settings_cache

    if _settings_cache is not None:
        return _settings_cache

    with _cache_lock:
        if _settings_cache is None:
            _settings_cache = _read_runtime_settings_sync()
        return _settings_cache


def clear_runtime_settings_cache() -> None:
    global _settings_cache
    with _cache_lock:
        _settings_cache = None


def get_llm_runtime_settings() -> LLMRuntimeSettings:
    values = _get_cached_runtime_settings()
    base_url = values.get(LLM_BASE_URL_KEY, "").strip()
    api_key = values.get(LLM_API_KEY_KEY, "").strip()
    model = values.get(LLM_MODEL_KEY, "").strip()

    missing_fields: list[str] = []
    if not base_url:
        missing_fields.append("llm_base_url")
    if not api_key:
        missing_fields.append("llm_api_key")
    if not model:
        missing_fields.append("llm_model")
    if missing_fields:
        raise ConfigError(
            "LLM is not fully configured. Missing system settings: "
            + ", ".join(missing_fields)
            + "."
        )

    return LLMRuntimeSettings(base_url=base_url, api_key=api_key, model=model)


def get_chat_max_messages() -> int:
    values = _get_cached_runtime_settings()
    raw = values.get(CHAT_MAX_MESSAGES_KEY, "").strip()
    try:
        return max(int(raw), 0)
    except (TypeError, ValueError):
        raise ConfigError(
            "System setting 'chat_max_messages' is invalid. Please update it in admin settings."
        )


def get_retrieval_top_k() -> int:
    values = _get_cached_runtime_settings()
    raw = values.get(RETRIEVAL_TOP_K_KEY, "").strip()
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        raise ConfigError(
            "System setting 'retrieval_top_k' is invalid. Please update it in admin settings."
        )

    if parsed <= 0:
        raise ConfigError("System setting 'retrieval_top_k' must be greater than 0.")
    return parsed


def mask_secret(secret: str) -> str:
    secret = secret.strip()
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


async def get_runtime_settings_payload() -> dict[str, dict[str, str | int]]:
    async with get_db() as db:
        repo = SystemSettingsRepository(db)
        values = await repo.get_many(_RUNTIME_SETTING_KEYS)

    llm_base_url = values.get(LLM_BASE_URL_KEY, settings.llm.base_url).strip()
    llm_api_key = values.get(LLM_API_KEY_KEY, settings.llm.api_key).strip()
    llm_model = values.get(LLM_MODEL_KEY, settings.llm.model).strip()
    chat_max_messages = values.get(
        CHAT_MAX_MESSAGES_KEY, str(settings.retrieval.max_messages)
    ).strip()
    retrieval_top_k = values.get(
        RETRIEVAL_TOP_K_KEY, str(settings.retrieval.top_k)
    ).strip()

    return {
        "llm": {
            "base_url": llm_base_url,
            "api_key_masked": mask_secret(llm_api_key),
            "api_key_configured": bool(llm_api_key),
            "model": llm_model,
        },
        "chat": {
            "max_messages": int(chat_max_messages),
        },
        "retrieval": {
            "top_k": int(retrieval_top_k),
        },
    }


async def update_runtime_settings(
    *,
    llm_base_url: str | None = None,
    llm_api_key: str | None = None,
    llm_model: str | None = None,
    chat_max_messages: int | None = None,
    retrieval_top_k: int | None = None,
) -> None:
    values: dict[str, str] = {}
    if llm_base_url is not None:
        values[LLM_BASE_URL_KEY] = llm_base_url.strip()
    if llm_api_key is not None:
        values[LLM_API_KEY_KEY] = llm_api_key.strip()
    if llm_model is not None:
        values[LLM_MODEL_KEY] = llm_model.strip()
    if chat_max_messages is not None:
        if chat_max_messages < 0:
            raise ConfigError("'chat_max_messages' must be greater than or equal to 0.")
        values[CHAT_MAX_MESSAGES_KEY] = str(chat_max_messages)
    if retrieval_top_k is not None:
        if retrieval_top_k <= 0:
            raise ConfigError("'retrieval_top_k' must be greater than 0.")
        values[RETRIEVAL_TOP_K_KEY] = str(retrieval_top_k)

    async with get_db() as db:
        repo = SystemSettingsRepository(db)
        await repo.upsert_many(values)

    clear_runtime_settings_cache()
