"""Runtime settings registry, defaults, and typed models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

from docmind.core.exceptions import ConfigError

RuntimeSettingCategory = Literal["runtime-required", "runtime-defaulted"]
RuntimeSettingType = Literal["str", "int", "bool"]
RuntimeSettingGroup = Literal[
    "qdrant",
    "llm",
    "ingestion",
    "retrieval",
    "chat",
    "confluence",
]

IMAGE_PROCESSOR_MULTIMODAL = "multimodal"
IMAGE_PROCESSOR_OCR = "ocr"
IMAGE_PROCESSOR_NONE = "none"
IMAGE_PROCESSOR_VALUES = frozenset(
    {IMAGE_PROCESSOR_MULTIMODAL, IMAGE_PROCESSOR_OCR, IMAGE_PROCESSOR_NONE}
)

DEFAULT_INGESTION_CHUNK_SIZE = 500
DEFAULT_INGESTION_CHUNK_OVERLAP = 50
DEFAULT_INGESTION_ENABLE_CODE_SUMMARIZATION = False
DEFAULT_INGESTION_IMAGE_PROCESSOR = IMAGE_PROCESSOR_NONE
DEFAULT_RETRIEVAL_TOP_K = 3
DEFAULT_CHAT_MAX_MESSAGES = 20
DEFAULT_RETRIEVAL_MAX_FULL_DOCS = 2
DEFAULT_RETRIEVAL_MAX_FULL_DOC_CHARS = 8000

QDRANT_URL_KEY = "qdrant_url"
LLM_BASE_URL_KEY = "llm_base_url"
LLM_API_KEY_KEY = "llm_api_key"
LLM_MODEL_KEY = "llm_model"
INGESTION_CHUNK_SIZE_KEY = "ingestion_chunk_size"
INGESTION_CHUNK_OVERLAP_KEY = "ingestion_chunk_overlap"
INGESTION_ENABLE_CODE_SUMMARIZATION_KEY = "ingestion_enable_code_summarization"
INGESTION_IMAGE_PROCESSOR_KEY = "ingestion_image_processor"
INGESTION_IMAGE_VISION_API_KEY_KEY = "ingestion_image_vision_api_key"
INGESTION_IMAGE_VISION_MODEL_KEY = "ingestion_image_vision_model"
INGESTION_IMAGE_VISION_BASE_URL_KEY = "ingestion_image_vision_base_url"
RETRIEVAL_TOP_K_KEY = "retrieval_top_k"
CHAT_MAX_MESSAGES_KEY = "chat_max_messages"
RETRIEVAL_MAX_FULL_DOCS_KEY = "retrieval_max_full_docs"
RETRIEVAL_MAX_FULL_DOC_CHARS_KEY = "retrieval_max_full_doc_chars"
CONFLUENCE_BASE_URL_KEY = "confluence_base_url"
CONFLUENCE_PAT_KEY = "confluence_pat"


@dataclass(frozen=True)
class RuntimeSettingSpec:
    key: str
    group: RuntimeSettingGroup
    field_name: str
    value_type: RuntimeSettingType
    category: RuntimeSettingCategory
    sensitive: bool = False
    default_value: str | None = None
    min_value: int | None = None
    max_value: int | None = None
    allowed_values: frozenset[str] | None = None


@dataclass(frozen=True)
class QdrantRuntimeSettings:
    url: str


@dataclass(frozen=True)
class LLMRuntimeSettings:
    base_url: str
    api_key: str
    model: str


@dataclass(frozen=True)
class ImageVisionRuntimeSettings:
    api_key: str
    model: str
    base_url: str


@dataclass(frozen=True)
class IngestionRuntimeSettings:
    chunk_size: int
    chunk_overlap: int
    enable_code_summarization: bool
    image_processor: str
    image_vision: ImageVisionRuntimeSettings


@dataclass(frozen=True)
class RetrievalRuntimeSettings:
    top_k: int
    max_full_docs: int
    max_full_doc_chars: int


@dataclass(frozen=True)
class ChatRuntimeSettings:
    max_messages: int


@dataclass(frozen=True)
class ConfluenceRuntimeSettings:
    base_url: str
    pat: str

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.pat)


@dataclass(frozen=True)
class RuntimeSettings:
    qdrant: QdrantRuntimeSettings
    llm: LLMRuntimeSettings
    ingestion: IngestionRuntimeSettings
    retrieval: RetrievalRuntimeSettings
    chat: ChatRuntimeSettings
    confluence: ConfluenceRuntimeSettings


RUNTIME_SETTING_SPECS: dict[str, RuntimeSettingSpec] = {
    QDRANT_URL_KEY: RuntimeSettingSpec(
        key=QDRANT_URL_KEY,
        group="qdrant",
        field_name="url",
        value_type="str",
        category="runtime-required",
    ),
    LLM_BASE_URL_KEY: RuntimeSettingSpec(
        key=LLM_BASE_URL_KEY,
        group="llm",
        field_name="base_url",
        value_type="str",
        category="runtime-required",
    ),
    LLM_API_KEY_KEY: RuntimeSettingSpec(
        key=LLM_API_KEY_KEY,
        group="llm",
        field_name="api_key",
        value_type="str",
        category="runtime-required",
        sensitive=True,
    ),
    LLM_MODEL_KEY: RuntimeSettingSpec(
        key=LLM_MODEL_KEY,
        group="llm",
        field_name="model",
        value_type="str",
        category="runtime-required",
    ),
    INGESTION_CHUNK_SIZE_KEY: RuntimeSettingSpec(
        key=INGESTION_CHUNK_SIZE_KEY,
        group="ingestion",
        field_name="chunk_size",
        value_type="int",
        category="runtime-defaulted",
        default_value=str(DEFAULT_INGESTION_CHUNK_SIZE),
        min_value=1,
    ),
    INGESTION_CHUNK_OVERLAP_KEY: RuntimeSettingSpec(
        key=INGESTION_CHUNK_OVERLAP_KEY,
        group="ingestion",
        field_name="chunk_overlap",
        value_type="int",
        category="runtime-defaulted",
        default_value=str(DEFAULT_INGESTION_CHUNK_OVERLAP),
        min_value=0,
    ),
    INGESTION_ENABLE_CODE_SUMMARIZATION_KEY: RuntimeSettingSpec(
        key=INGESTION_ENABLE_CODE_SUMMARIZATION_KEY,
        group="ingestion",
        field_name="enable_code_summarization",
        value_type="bool",
        category="runtime-defaulted",
        default_value="false",
    ),
    INGESTION_IMAGE_PROCESSOR_KEY: RuntimeSettingSpec(
        key=INGESTION_IMAGE_PROCESSOR_KEY,
        group="ingestion",
        field_name="image_processor",
        value_type="str",
        category="runtime-defaulted",
        default_value=DEFAULT_INGESTION_IMAGE_PROCESSOR,
        allowed_values=IMAGE_PROCESSOR_VALUES,
    ),
    INGESTION_IMAGE_VISION_API_KEY_KEY: RuntimeSettingSpec(
        key=INGESTION_IMAGE_VISION_API_KEY_KEY,
        group="ingestion",
        field_name="image_vision_api_key",
        value_type="str",
        category="runtime-required",
        sensitive=True,
    ),
    INGESTION_IMAGE_VISION_MODEL_KEY: RuntimeSettingSpec(
        key=INGESTION_IMAGE_VISION_MODEL_KEY,
        group="ingestion",
        field_name="image_vision_model",
        value_type="str",
        category="runtime-required",
    ),
    INGESTION_IMAGE_VISION_BASE_URL_KEY: RuntimeSettingSpec(
        key=INGESTION_IMAGE_VISION_BASE_URL_KEY,
        group="ingestion",
        field_name="image_vision_base_url",
        value_type="str",
        category="runtime-required",
    ),
    RETRIEVAL_TOP_K_KEY: RuntimeSettingSpec(
        key=RETRIEVAL_TOP_K_KEY,
        group="retrieval",
        field_name="top_k",
        value_type="int",
        category="runtime-defaulted",
        default_value=str(DEFAULT_RETRIEVAL_TOP_K),
        min_value=1,
    ),
    CHAT_MAX_MESSAGES_KEY: RuntimeSettingSpec(
        key=CHAT_MAX_MESSAGES_KEY,
        group="chat",
        field_name="max_messages",
        value_type="int",
        category="runtime-defaulted",
        default_value=str(DEFAULT_CHAT_MAX_MESSAGES),
        min_value=0,
    ),
    RETRIEVAL_MAX_FULL_DOCS_KEY: RuntimeSettingSpec(
        key=RETRIEVAL_MAX_FULL_DOCS_KEY,
        group="retrieval",
        field_name="max_full_docs",
        value_type="int",
        category="runtime-defaulted",
        default_value=str(DEFAULT_RETRIEVAL_MAX_FULL_DOCS),
        min_value=1,
    ),
    RETRIEVAL_MAX_FULL_DOC_CHARS_KEY: RuntimeSettingSpec(
        key=RETRIEVAL_MAX_FULL_DOC_CHARS_KEY,
        group="retrieval",
        field_name="max_full_doc_chars",
        value_type="int",
        category="runtime-defaulted",
        default_value=str(DEFAULT_RETRIEVAL_MAX_FULL_DOC_CHARS),
        min_value=1,
    ),
    CONFLUENCE_BASE_URL_KEY: RuntimeSettingSpec(
        key=CONFLUENCE_BASE_URL_KEY,
        group="confluence",
        field_name="base_url",
        value_type="str",
        category="runtime-required",
    ),
    CONFLUENCE_PAT_KEY: RuntimeSettingSpec(
        key=CONFLUENCE_PAT_KEY,
        group="confluence",
        field_name="pat",
        value_type="str",
        category="runtime-required",
        sensitive=True,
    ),
}

RUNTIME_SETTING_KEYS = list(RUNTIME_SETTING_SPECS)


def get_runtime_setting_defaults() -> dict[str, str]:
    return {
        key: spec.default_value
        for key, spec in RUNTIME_SETTING_SPECS.items()
        if spec.default_value is not None
    }


def get_runtime_setting_bootstrap_values() -> dict[str, str]:
    return get_runtime_setting_defaults()


def mask_secret(secret: str) -> str:
    secret = secret.strip()
    if not secret:
        return ""
    if len(secret) <= 8:
        return "*" * len(secret)
    return f"{secret[:4]}{'*' * (len(secret) - 8)}{secret[-4:]}"


def serialize_runtime_value(spec: RuntimeSettingSpec, value: object) -> str:
    if spec.value_type == "bool":
        if not isinstance(value, bool):
            raise ConfigError(f"System setting '{spec.key}' must be a boolean.")
        return "true" if value else "false"
    if spec.value_type == "int":
        if not isinstance(value, int):
            raise ConfigError(f"System setting '{spec.key}' must be an integer.")
        return str(value)
    if value is None:
        return ""
    return str(value).strip()


def _parse_bool(raw: str, key: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"System setting '{key}' is invalid. Expected a boolean string.")


def _parse_spec_value(spec: RuntimeSettingSpec, raw: str) -> str | int | bool:
    if spec.value_type == "str":
        value = raw.strip()
        if spec.allowed_values and value and value not in spec.allowed_values:
            raise ConfigError(
                f"System setting '{spec.key}' must be one of: "
                + ", ".join(sorted(spec.allowed_values))
            )
        return value

    if spec.value_type == "bool":
        return _parse_bool(raw, spec.key)

    try:
        parsed = int(raw.strip())
    except (TypeError, ValueError):
        raise ConfigError(
            f"System setting '{spec.key}' is invalid. Expected an integer value."
        )

    if spec.min_value is not None and parsed < spec.min_value:
        raise ConfigError(
            f"System setting '{spec.key}' must be greater than or equal to {spec.min_value}."
        )
    if spec.max_value is not None and parsed > spec.max_value:
        raise ConfigError(
            f"System setting '{spec.key}' must be less than or equal to {spec.max_value}."
        )
    return parsed


def build_runtime_settings(raw_values: Mapping[str, str]) -> RuntimeSettings:
    merged: dict[str, str] = {}
    for key, spec in RUNTIME_SETTING_SPECS.items():
        if key in raw_values:
            merged[key] = str(raw_values[key])
        elif spec.default_value is not None:
            merged[key] = spec.default_value
        else:
            merged[key] = ""

    parsed = {
        key: _parse_spec_value(spec, merged[key])
        for key, spec in RUNTIME_SETTING_SPECS.items()
    }

    image_processor = str(parsed[INGESTION_IMAGE_PROCESSOR_KEY])

    return RuntimeSettings(
        qdrant=QdrantRuntimeSettings(
            url=str(parsed[QDRANT_URL_KEY]),
        ),
        llm=LLMRuntimeSettings(
            base_url=str(parsed[LLM_BASE_URL_KEY]),
            api_key=str(parsed[LLM_API_KEY_KEY]),
            model=str(parsed[LLM_MODEL_KEY]),
        ),
        ingestion=IngestionRuntimeSettings(
            chunk_size=int(parsed[INGESTION_CHUNK_SIZE_KEY]),
            chunk_overlap=int(parsed[INGESTION_CHUNK_OVERLAP_KEY]),
            enable_code_summarization=bool(
                parsed[INGESTION_ENABLE_CODE_SUMMARIZATION_KEY]
            ),
            image_processor=image_processor,
            image_vision=ImageVisionRuntimeSettings(
                api_key=str(parsed[INGESTION_IMAGE_VISION_API_KEY_KEY]),
                model=str(parsed[INGESTION_IMAGE_VISION_MODEL_KEY]),
                base_url=str(parsed[INGESTION_IMAGE_VISION_BASE_URL_KEY]),
            ),
        ),
        retrieval=RetrievalRuntimeSettings(
            top_k=int(parsed[RETRIEVAL_TOP_K_KEY]),
            max_full_docs=int(parsed[RETRIEVAL_MAX_FULL_DOCS_KEY]),
            max_full_doc_chars=int(parsed[RETRIEVAL_MAX_FULL_DOC_CHARS_KEY]),
        ),
        chat=ChatRuntimeSettings(
            max_messages=int(parsed[CHAT_MAX_MESSAGES_KEY]),
        ),
        confluence=ConfluenceRuntimeSettings(
            base_url=str(parsed[CONFLUENCE_BASE_URL_KEY]),
            pat=str(parsed[CONFLUENCE_PAT_KEY]),
        ),
    )


def _build_status(
    *,
    configured: bool,
    missing_fields: list[str],
    configured_message: str,
    missing_message: str,
) -> dict[str, object]:
    return {
        "configured": configured,
        "missing_fields": missing_fields,
        "message": configured_message if configured else missing_message,
    }


def get_runtime_settings_statuses(
    settings: RuntimeSettings,
) -> dict[str, dict[str, object]]:
    qdrant_missing_fields = [QDRANT_URL_KEY] if not settings.qdrant.url.strip() else []
    llm_missing_fields = [
        key
        for key, value in (
            (LLM_BASE_URL_KEY, settings.llm.base_url),
            (LLM_API_KEY_KEY, settings.llm.api_key),
            (LLM_MODEL_KEY, settings.llm.model),
        )
        if not value.strip()
    ]
    image_vision_missing_fields = [
        key
        for key, value in (
            (
                INGESTION_IMAGE_VISION_BASE_URL_KEY,
                settings.ingestion.image_vision.base_url,
            ),
            (INGESTION_IMAGE_VISION_MODEL_KEY, settings.ingestion.image_vision.model),
            (
                INGESTION_IMAGE_VISION_API_KEY_KEY,
                settings.ingestion.image_vision.api_key,
            ),
        )
        if not value.strip()
    ]
    confluence_missing_fields = []
    if not settings.confluence.base_url.strip():
        confluence_missing_fields.append(CONFLUENCE_BASE_URL_KEY)
    if not settings.confluence.pat.strip():
        confluence_missing_fields.append(CONFLUENCE_PAT_KEY)

    return {
        "qdrant": _build_status(
            configured=not qdrant_missing_fields,
            missing_fields=qdrant_missing_fields,
            configured_message="Qdrant is configured.",
            missing_message="Qdrant URL is required.",
        ),
        "llm": _build_status(
            configured=not llm_missing_fields,
            missing_fields=llm_missing_fields,
            configured_message="LLM is configured.",
            missing_message="LLM is not fully configured.",
        ),
        "image_vision": _build_status(
            configured=not image_vision_missing_fields,
            missing_fields=image_vision_missing_fields,
            configured_message="Image vision is configured.",
            missing_message="Image vision is not fully configured.",
        ),
        "confluence": _build_status(
            configured=not confluence_missing_fields,
            missing_fields=confluence_missing_fields,
            configured_message="Confluence is configured.",
            missing_message="Confluence requires both Base URL and PAT.",
        ),
    }


def runtime_settings_to_payload(
    settings: RuntimeSettings,
) -> dict[str, dict[str, object]]:
    statuses = get_runtime_settings_statuses(settings)
    return {
        "qdrant": {
            "url": settings.qdrant.url,
            "configured": bool(statuses["qdrant"]["configured"]),
            "status": statuses["qdrant"],
        },
        "llm": {
            "base_url": settings.llm.base_url,
            "api_key": settings.llm.api_key,
            "model": settings.llm.model,
            "configured": bool(statuses["llm"]["configured"]),
            "status": statuses["llm"],
            "api_key_masked": mask_secret(settings.llm.api_key),
            "api_key_configured": bool(settings.llm.api_key.strip()),
        },
        "ingestion": {
            "chunk_size": settings.ingestion.chunk_size,
            "chunk_overlap": settings.ingestion.chunk_overlap,
            "enable_code_summarization": settings.ingestion.enable_code_summarization,
            "image_processor": settings.ingestion.image_processor,
            "image_vision_api_key": settings.ingestion.image_vision.api_key,
            "image_vision_base_url": settings.ingestion.image_vision.base_url,
            "image_vision_model": settings.ingestion.image_vision.model,
            "image_vision_configured": bool(statuses["image_vision"]["configured"]),
            "image_vision_status": statuses["image_vision"],
            "image_vision_api_key_masked": mask_secret(
                settings.ingestion.image_vision.api_key
            ),
            "image_vision_api_key_configured": bool(
                settings.ingestion.image_vision.api_key.strip()
            ),
        },
        "chat": {
            "max_messages": settings.chat.max_messages,
        },
        "retrieval": {
            "top_k": settings.retrieval.top_k,
            "max_full_docs": settings.retrieval.max_full_docs,
            "max_full_doc_chars": settings.retrieval.max_full_doc_chars,
        },
        "confluence": {
            "base_url": settings.confluence.base_url,
            "pat": settings.confluence.pat,
            "enabled": bool(statuses["confluence"]["configured"]),
            "configured": bool(statuses["confluence"]["configured"]),
            "status": statuses["confluence"],
            "pat_masked": mask_secret(settings.confluence.pat),
            "pat_configured": bool(settings.confluence.pat.strip()),
        },
    }
