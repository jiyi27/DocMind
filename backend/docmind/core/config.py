"""Application configuration loaded from environment variables.

All configuration values are required and must be provided via environment
variables (or a .env file). There are no code-level defaults — missing
variables are collected and reported at startup, then the process exits.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _require_str(env_var: str) -> str:
    """Return the value of *env_var*, recording it as missing if absent/empty."""
    value = os.getenv(env_var, "").strip()
    if not value:
        _MISSING.append(env_var)
    return value


def _require_int(env_var: str) -> int:
    """Return *env_var* parsed as int, recording it as missing/invalid if needed."""
    raw = os.getenv(env_var, "").strip()
    if not raw:
        _MISSING.append(env_var)
        return 0  # sentinel; process will exit before this value is used
    try:
        return int(raw)
    except (ValueError, TypeError):
        _MISSING.append(f"{env_var} (value {raw!r} is not a valid integer)")
        return 0


# Accumulates names of missing / invalid env vars during module import.
_MISSING: list[str] = []

# ---------------------------------------------------------------------------
# Config dataclasses — no defaults, every field reads from env
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding service configuration (OpenAI-compatible, provider-agnostic)."""

    base_url: str
    api_key: str
    model: str


@dataclass(frozen=True)
class QdrantConfig:
    """Qdrant vector database configuration."""

    url: str
    collection: str


@dataclass(frozen=True)
class LLMConfig:
    """LLM configuration."""

    api_key: str
    model: str
    base_url: str


@dataclass(frozen=True)
class IngestionConfig:
    """Document ingestion pipeline configuration."""

    chunk_size: int
    chunk_overlap: int


@dataclass(frozen=True)
class RetrievalConfig:
    """Retrieval pipeline configuration."""

    top_k: int
    max_messages: int  # Max number of messages to keep in conversation history (oldest are dropped first).


@dataclass(frozen=True)
class LogConfig:
    """Logging configuration."""

    dir: str
    # Minimum level to write: "debug" | "info" | "error"
    level: str


@dataclass(frozen=True)
class JWTConfig:
    """JWT authentication configuration."""

    secret_key: str
    algorithm: str
    expire_minutes: int


@dataclass(frozen=True)
class AdminConfig:
    """
    Super-admin access control configuration.

    super_admin_usernames: Comma-separated list of usernames that are granted
        super-admin privileges (e.g. creating / deleting knowledge bases and
        other privileged operations).  These users must still authenticate via
        JWT — this list only controls *what* they are allowed to do after login.

        Example env value:  SUPER_ADMIN_USERNAMES=super_admin,alice,bob
    """

    super_admin_usernames: frozenset[str]


@dataclass(frozen=True)
class CORSConfig:
    """
    CORS configuration.

    allowed_origins: Comma-separated list of allowed origins.
        Use "*" to allow all origins (not recommended for production).

        Example env value:  CORS_ORIGINS=http://localhost:3000,https://app.example.com
    """

    allowed_origins: list[str]


@dataclass(frozen=True)
class Settings:
    """Root settings aggregating all sub-configurations."""

    embedding: EmbeddingConfig
    qdrant: QdrantConfig
    llm: LLMConfig
    ingestion: IngestionConfig
    retrieval: RetrievalConfig
    log: LogConfig
    jwt: JWTConfig
    admin: AdminConfig
    cors: CORSConfig

    def validate(self) -> list[str]:
        """Return the list of missing / invalid environment variables collected at import time."""
        return list(_MISSING)


def _build_settings() -> Settings:
    """Construct Settings by reading all required environment variables."""
    return Settings(
        embedding=EmbeddingConfig(
            base_url=_require_str("EMBEDDING_BASE_URL"),
            api_key=_require_str("EMBEDDING_API_KEY"),
            model=_require_str("EMBEDDING_MODEL"),
        ),
        qdrant=QdrantConfig(
            url=_require_str("QDRANT_URL"),
            collection="docmind",  # base prefix; actual collections are docmind_{kb_name}
        ),
        jwt=JWTConfig(
            secret_key=_require_str("JWT_SECRET_KEY"),
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            expire_minutes=_require_int("JWT_EXPIRE_MINUTES"),
        ),
        llm=LLMConfig(
            api_key=_require_str("LLM_API_KEY"),
            model=_require_str("LLM_MODEL"),
            base_url=_require_str("LLM_BASE_URL"),
        ),
        ingestion=IngestionConfig(
            chunk_size=_require_int("CHUNK_SIZE"),
            chunk_overlap=_require_int("CHUNK_OVERLAP"),
        ),
        retrieval=RetrievalConfig(
            top_k=_require_int("TOP_K"),
            max_messages=_require_int("MAX_MESSAGES"),
        ),
        log=LogConfig(
            dir=_require_str("LOG_DIR"),
            level=_require_str("LOG_LEVEL"),
        ),
        admin=AdminConfig(
            super_admin_usernames=frozenset(
                name.strip()
                for name in os.getenv("SUPER_ADMIN_USERNAMES", "").split(",")
                if name.strip()
            ),
        ),
        cors=CORSConfig(
            allowed_origins=[
                origin.strip()
                for origin in os.getenv("CORS_ORIGINS", "*").split(",")
                if origin.strip()
            ],
        ),
    )


# Singleton — import `settings` wherever needed.
# Missing variables are recorded during construction; call settings.validate()
# at startup and abort if the returned list is non-empty.
settings = _build_settings()
