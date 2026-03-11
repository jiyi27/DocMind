"""LLM factory — single source of truth for the chat model instance."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from docmind.core.config import settings


def get_llm() -> ChatOpenAI:
    """Return the configured ChatOpenAI instance (OpenRouter-compatible)."""
    return ChatOpenAI(
        api_key=settings.llm.api_key,
        base_url=settings.llm.base_url,
        model=settings.llm.model,
    )
