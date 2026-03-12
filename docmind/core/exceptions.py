"""Application-level exception hierarchy.

All exceptions that inherit from ``AppException`` carry a user-visible
``message`` that is safe to return to the client.  Unknown exceptions that do
*not* inherit from ``AppException`` are caught by the global handler, logged,
and replaced with a generic message so that internal details are never leaked.

Hierarchy
---------
AppException
├── DocumentError      – file type not supported, parse failure, etc.
├── VectorStoreError   – Qdrant unreachable or misconfigured
├── LLMError           – LLM call failed (including context-window overflow)
└── ConfigError        – missing API keys or invalid service configuration
"""

from __future__ import annotations


class AppException(Exception):
    """Base class for all application business exceptions.

    Parameters
    ----------
    message:
        Human-readable description that is safe to expose to the client.
        Falls back to ``default_message`` when omitted.
    """

    default_message: str = "An unexpected error occurred. Please try again later."

    def __init__(self, message: str | None = None) -> None:
        self.message: str = message or self.default_message
        super().__init__(self.message)


class DocumentError(AppException):
    """Raised for any document-related failure (unsupported type, parse error, etc.)."""

    default_message = "The document could not be processed. Please check the file and try again."


class VectorStoreError(AppException):
    """Raised when the vector store (Qdrant) cannot be reached or is misconfigured."""

    default_message = "The knowledge base service is temporarily unavailable. Please try again later."


class LLMError(AppException):
    """Raised when the LLM call fails (network error, context-window overflow, etc.)."""

    default_message = "The AI service is temporarily unavailable. Please try again later."


class ConfigError(AppException):
    """Raised when a required service cannot be initialised due to missing configuration."""

    default_message = "A service configuration error occurred. Please contact the administrator."
