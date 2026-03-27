"""Runtime-editable system settings backed by SQLite."""

from __future__ import annotations

from dataclasses import dataclass
import threading
from typing import Any

from docmind.core.exceptions import ConfigError
from docmind.db.database import create_sync_connection, get_db
from docmind.db.repositories import SystemSettingsRepository
from docmind.services.system_settings_registry import (
    CHAT_MAX_MESSAGES_KEY,
    LLM_API_KEY_KEY,
    LLM_BASE_URL_KEY,
    LLM_MODEL_KEY,
    RETRIEVAL_TOP_K_KEY,
    RUNTIME_SETTING_KEYS,
    RUNTIME_SETTING_SPECS,
    get_runtime_setting_defaults,
)

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
        placeholders = ",".join("?" for _ in RUNTIME_SETTING_KEYS)
        query = f"SELECT key, value FROM system_settings WHERE key IN ({placeholders})"
        rows = conn.execute(query, tuple(RUNTIME_SETTING_KEYS)).fetchall()
        values = {str(row["key"]): str(row["value"]) for row in rows}
    finally:
        conn.close()

    defaults = get_runtime_setting_defaults()
    return {key: values.get(key, default) for key, default in defaults.items()}


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


def _require_string_setting(key: str) -> str:
    value = _get_cached_runtime_settings().get(key, "").strip()
    if not value:
        raise ConfigError(
            f"System setting '{key}' is missing. Please update it in admin settings."
        )
    return value


def _require_int_setting(key: str, *, min_value: int | None = None) -> int:
    raw = _get_cached_runtime_settings().get(key, "").strip()
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        raise ConfigError(
            f"System setting '{key}' is invalid. Please update it in admin settings."
        )

    if min_value is not None and parsed < min_value:
        comparator = (
            "greater than 0"
            if min_value == 1
            else f"greater than or equal to {min_value}"
        )
        raise ConfigError(f"System setting '{key}' must be {comparator}.")
    return parsed


def get_llm_runtime_settings() -> LLMRuntimeSettings:
    values = _get_cached_runtime_settings()

    missing_fields: list[str] = []
    for key in (LLM_BASE_URL_KEY, LLM_API_KEY_KEY, LLM_MODEL_KEY):
        if not values.get(key, "").strip():
            missing_fields.append(key)
    if missing_fields:
        raise ConfigError(
            "LLM is not fully configured. Missing system settings: "
            + ", ".join(missing_fields)
            + "."
        )

    return LLMRuntimeSettings(
        base_url=_require_string_setting(LLM_BASE_URL_KEY),
        api_key=_require_string_setting(LLM_API_KEY_KEY),
        model=_require_string_setting(LLM_MODEL_KEY),
    )


def get_chat_max_messages() -> int:
    return _require_int_setting(CHAT_MAX_MESSAGES_KEY, min_value=0)


def get_retrieval_top_k() -> int:
    return _require_int_setting(RETRIEVAL_TOP_K_KEY, min_value=1)


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
        values = await repo.get_many(RUNTIME_SETTING_KEYS)

    merged_values = {**get_runtime_setting_defaults(), **values}
    payload: dict[str, dict[str, Any]] = {"llm": {}, "chat": {}, "retrieval": {}}
    for key, spec in RUNTIME_SETTING_SPECS.items():
        raw_value = merged_values.get(key, "").strip()
        if spec.sensitive:
            payload[spec.group]["api_key_masked"] = mask_secret(raw_value)
            payload[spec.group]["api_key_configured"] = bool(raw_value)
            continue

        if spec.value_type == "int":
            payload[spec.group][spec.field_name] = int(raw_value)
        else:
            payload[spec.group][spec.field_name] = raw_value

    return payload


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
