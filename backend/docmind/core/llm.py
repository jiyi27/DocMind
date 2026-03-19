"""LLM factory — single source of truth for chat model instances.

Uses a cached singleton to avoid re-creating the client on every call.
"""

from __future__ import annotations

import threading

from langchain_openai import ChatOpenAI

from docmind.core.config import settings
from docmind.core import logger
from docmind.core.exceptions import ConfigError

_llm_instance: ChatOpenAI | None = None
_image_llm_instance: ChatOpenAI | None = None
_lock = threading.Lock()

# Legacy alias kept for any existing catch sites.
LLMConfigError = ConfigError


def get_llm() -> ChatOpenAI:
    """Return the configured ChatOpenAI instance (OpenRouter-compatible, cached singleton).

    Raises
    ------
    LLMConfigError
        If LLM_API_KEY is empty.
    """
    global _llm_instance

    if _llm_instance is not None:
        return _llm_instance

    with _lock:
        if _llm_instance is not None:
            return _llm_instance

        if not settings.llm.api_key:
            logger.error("llm_init_failed", {"reason": "LLM_API_KEY is not configured"})
            raise ConfigError(
                "LLM_API_KEY is not configured. Please set it in your environment."
            )

        _llm_instance = ChatOpenAI(
            api_key=settings.llm.api_key,
            base_url=settings.llm.base_url,
            model=settings.llm.model,
        )
        return _llm_instance


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
