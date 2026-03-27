"""LLM factory — single source of truth for chat model instances.

Uses a cached singleton to avoid re-creating the client on every call.
"""

from __future__ import annotations

import threading

from langchain_openai import ChatOpenAI

from docmind.core.config import settings
from docmind.core import logger
from docmind.core.exceptions import ConfigError
from docmind.services.system_settings import get_llm_runtime_settings

_llm_instances: dict[tuple[str, str, str], ChatOpenAI] = {}
_image_llm_instance: ChatOpenAI | None = None
_lock = threading.Lock()

# Legacy alias kept for any existing catch sites.
LLMConfigError = ConfigError


def get_llm() -> ChatOpenAI:
    """Return the configured ChatOpenAI instance (runtime-configurable, cached).

    Raises
    ------
    LLMConfigError
        If the runtime LLM settings are incomplete.
    """
    runtime = get_llm_runtime_settings()
    cache_key = (runtime.base_url, runtime.model, runtime.api_key)

    if cache_key in _llm_instances:
        return _llm_instances[cache_key]

    with _lock:
        if cache_key in _llm_instances:
            return _llm_instances[cache_key]

        try:
            instance = ChatOpenAI(
                api_key=runtime.api_key,
                base_url=runtime.base_url,
                model=runtime.model,
            )
        except ConfigError:
            raise
        except Exception as exc:
            logger.error(
                "llm_init_failed",
                {
                    "reason": str(exc),
                    "base_url": runtime.base_url,
                    "model": runtime.model,
                },
                exc=exc,
            )
            raise

        _llm_instances[cache_key] = instance
        return instance


def clear_llm_cache() -> None:
    with _lock:
        _llm_instances.clear()


def get_image_llm() -> ChatOpenAI:
    """Return the configured vision ChatOpenAI instance for image summarization.

    Raises
    ------
    LLMConfigError
        If IMAGE_VISION_API_KEY is empty when multimodal image processing is enabled.
    """
    global _image_llm_instance

    if _image_llm_instance is not None:
        return _image_llm_instance

    with _lock:
        if _image_llm_instance is not None:
            return _image_llm_instance

        vision = settings.ingestion.image_vision
        if not vision.api_key:
            logger.error(
                "image_llm_init_failed",
                {"reason": "IMAGE_VISION_API_KEY is not configured"},
            )
            raise ConfigError(
                "IMAGE_VISION_API_KEY is not configured. "
                "Please set it in your environment."
            )

        _image_llm_instance = ChatOpenAI(
            api_key=vision.api_key,
            base_url=vision.base_url,
            model=vision.model,
            max_tokens=512,
        )
        return _image_llm_instance
