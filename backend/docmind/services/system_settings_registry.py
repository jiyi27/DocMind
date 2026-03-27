"""Registry for runtime-editable system settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from docmind.core.config import settings

LLM_BASE_URL_KEY = "llm_base_url"
LLM_API_KEY_KEY = "llm_api_key"
LLM_MODEL_KEY = "llm_model"
CHAT_MAX_MESSAGES_KEY = "chat_max_messages"
RETRIEVAL_TOP_K_KEY = "retrieval_top_k"


@dataclass(frozen=True)
class RuntimeSettingSpec:
    key: str
    group: Literal["llm", "chat", "retrieval"]
    field_name: str
    value_type: Literal["str", "int"]
    sensitive: bool = False

    def default_value(self) -> str:
        if self.key in (LLM_BASE_URL_KEY, LLM_API_KEY_KEY, LLM_MODEL_KEY):
            return ""
        if self.key == CHAT_MAX_MESSAGES_KEY:
            return str(settings.retrieval.max_messages)
        if self.key == RETRIEVAL_TOP_K_KEY:
            return str(settings.retrieval.top_k)
        raise KeyError(f"Unknown runtime setting key: {self.key}")


RUNTIME_SETTING_SPECS: dict[str, RuntimeSettingSpec] = {
    LLM_BASE_URL_KEY: RuntimeSettingSpec(
        key=LLM_BASE_URL_KEY,
        group="llm",
        field_name="base_url",
        value_type="str",
    ),
    LLM_API_KEY_KEY: RuntimeSettingSpec(
        key=LLM_API_KEY_KEY,
        group="llm",
        field_name="api_key",
        value_type="str",
        sensitive=True,
    ),
    LLM_MODEL_KEY: RuntimeSettingSpec(
        key=LLM_MODEL_KEY,
        group="llm",
        field_name="model",
        value_type="str",
    ),
    CHAT_MAX_MESSAGES_KEY: RuntimeSettingSpec(
        key=CHAT_MAX_MESSAGES_KEY,
        group="chat",
        field_name="max_messages",
        value_type="int",
    ),
    RETRIEVAL_TOP_K_KEY: RuntimeSettingSpec(
        key=RETRIEVAL_TOP_K_KEY,
        group="retrieval",
        field_name="top_k",
        value_type="int",
    ),
}

RUNTIME_SETTING_KEYS = list(RUNTIME_SETTING_SPECS)


def get_runtime_setting_defaults() -> dict[str, str]:
    return {key: spec.default_value() for key, spec in RUNTIME_SETTING_SPECS.items()}


def get_runtime_setting_bootstrap_values() -> dict[str, str]:
    """Return only non-empty values that should be seeded into SQLite."""
    values: dict[str, str] = {}
    for key, spec in RUNTIME_SETTING_SPECS.items():
        value = spec.default_value().strip()
        if value:
            values[key] = value
    return values
