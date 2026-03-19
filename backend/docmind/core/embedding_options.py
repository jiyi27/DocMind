"""Embedding provider option registry for KB creation UX."""

from __future__ import annotations

from typing import Any

EMBEDDING_OPTION_REGISTRY: dict[str, dict[str, Any]] = {
    "openai_compatible": {
        "label": "OpenAI-Compatible API",
        "description": "Use OpenAI or any OpenAI-compatible embedding endpoint.",
        "fields": [
            {
                "name": "model",
                "label": "Model",
                "type": "text",
                "required": True,
                "placeholder": "e.g. text-embedding-3-small or nomic-embed-text:latest",
                "help": "Required. This model will be bound to the knowledge base.",
            },
            {
                "name": "base_url",
                "label": "Base URL",
                "type": "text",
                "required": True,
                "placeholder": "e.g. https://api.openai.com/v1",
                "help": "Required. Enter the exact OpenAI-compatible embedding endpoint for this knowledge base.",
            },
            {
                "name": "api_key",
                "label": "API Key",
                "type": "password",
                "required": True,
                "placeholder": "e.g. sk-xxx or ollama",
                "help": "Required. Enter the API key or provider token used by this endpoint.",
                "sensitive": True,
            },
        ],
    },
    "huggingface": {
        "label": "HuggingFace Local Model",
        "description": "Load a HuggingFace embedding model on the server.",
        "fields": [
            {
                "name": "model",
                "label": "Model",
                "type": "text",
                "required": True,
                "placeholder": "e.g. BAAI/bge-small-en-v1.5",
                "help": "Required. The model name must be available to the server runtime.",
            }
        ],
    },
}

EMBEDDING_CREATION_HINT = (
    "Embedding settings are bound to the knowledge base at creation time. "
    "Provider, model, and vector dimension should be treated as immutable after creation."
)


def list_embedding_options() -> dict[str, Any]:
    """Return frontend-safe embedding provider metadata for KB creation."""
    providers: list[dict[str, Any]] = []

    for value, option in EMBEDDING_OPTION_REGISTRY.items():
        providers.append(
            {
                "value": value,
                "label": option["label"],
                "description": option["description"],
                "fields": option["fields"],
            }
        )

    return {
        "default_provider": "openai_compatible",
        "creation_hint": EMBEDDING_CREATION_HINT,
        "providers": providers,
    }
