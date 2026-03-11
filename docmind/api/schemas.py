"""Pydantic request / response schemas for the API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ── Ingestion ──────────────────────────────────────────────


class IngestMetadata(BaseModel):
    """Optional metadata attached to an ingested document."""

    title: str = ""
    url: str = ""
    category: str = "none"
    business_line: str = "none"
    audience: str = "all"


class IngestResponse(BaseModel):
    """Response after a successful document ingestion."""

    status: str
    chunk_count: int
    file_name: str


# ── Chat ───────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Incoming chat request — mirrors the n8n Webhook body."""

    chat_input: str = Field(..., alias="chatInput", description="The user's question")
    session_id: str = Field(default="default", alias="sessionId")


class ChatResponse(BaseModel):
    """Response from the RAG chat endpoint."""

    answer: str
    sources: list[str] = []
    session_id: str
