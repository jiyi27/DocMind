"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding service configuration (OpenAI-compatible, provider-agnostic)."""
    base_url: str = field(default_factory=lambda: os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434/v1"))
    api_key: str = field(default_factory=lambda: os.getenv("EMBEDDING_API_KEY", "ollama"))
    model: str = field(default_factory=lambda: os.getenv("EMBEDDING_MODEL", "nomic-embed-text:latest"))


@dataclass(frozen=True)
class QdrantConfig:
    """Qdrant vector database configuration."""
    url: str = field(default_factory=lambda: os.getenv("QDRANT_URL", "http://localhost:6333"))
    collection: str = field(default_factory=lambda: os.getenv("QDRANT_COLLECTION", "knowledge_base"))


@dataclass(frozen=True)
class LLMConfig:
    """LLM (OpenRouter) configuration."""
    api_key: str = field(default_factory=lambda: os.getenv("LLM_API_KEY", ""))
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "google/gemini-2.5-flash"))
    base_url: str = field(default_factory=lambda: os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"))


@dataclass(frozen=True)
class IngestionConfig:
    """Document ingestion pipeline configuration."""
    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "500")))
    chunk_overlap: int = field(default_factory=lambda: int(os.getenv("CHUNK_OVERLAP", "50")))


@dataclass(frozen=True)
class RetrievalConfig:
    """Retrieval pipeline configuration."""
    top_k: int = field(default_factory=lambda: int(os.getenv("TOP_K", "3")))


@dataclass(frozen=True)
class Settings:
    """Root settings aggregating all sub-configurations."""
    embedding: EmbeddingConfig = field(default_factory=EmbeddingConfig)
    qdrant: QdrantConfig = field(default_factory=QdrantConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    retrieval: RetrievalConfig = field(default_factory=RetrievalConfig)


# Singleton — import `settings` wherever needed
settings = Settings()
