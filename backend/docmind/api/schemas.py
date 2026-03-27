from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from docmind.ingestion.constants import DEFAULT_RETRIEVAL_MODE
from docmind.services.system_settings import get_runtime_settings


class DocumentMetadata(BaseModel):
    """Business metadata attached to an ingested document."""

    title: str = ""
    url: str = ""


class IngestionOptions(BaseModel):
    """Runtime controls that affect how a document is processed."""

    retrieval_mode: Literal["chunk", "full_doc"] = Field(
        default=DEFAULT_RETRIEVAL_MODE,
        description="'chunk': retrieve individual chunks. 'full_doc': retrieve the full article when any chunk matches.",
    )
    chunk_size: int = Field(
        default_factory=lambda: get_runtime_settings().ingestion.chunk_size,
        description="Target chunk size for semantic merging.",
    )
    chunk_overlap: int = Field(
        default_factory=lambda: get_runtime_settings().ingestion.chunk_overlap,
        description="Overlap budget between adjacent chunks.",
    )


class ChatRequest(BaseModel):
    chat_input: str = Field(..., alias="chatInput", description="The user's question")
    session_id: str = Field(..., alias="sessionId", description="Chat session UUID")


class ChatSessionCreate(BaseModel):
    title: str = Field(default="New Conversation")
    kb_id: str | None = None


class ChatMessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    sources: list[str] = Field(default_factory=list)
    model_name: str = ""
    token_count: int = 0


class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query string")
    kb_name: str = Field(
        ..., alias="kbName", description="Knowledge base slug to search in"
    )
    top_k: int = Field(
        default=5, alias="topK", ge=1, le=50, description="Number of results to return"
    )


class SearchResultItem(BaseModel):
    title: str
    url: str
    source_label: str = Field(alias="sourceLabel")
    score: float
    matched_content: str = Field(alias="matchedContent")
    matched_chunk_type: str = Field(alias="matchedChunkType")
    retrieval_mode: str = Field(alias="retrievalMode")


class SearchResponse(BaseModel):
    results: list[SearchResultItem]


class DocumentListItem(BaseModel):
    id: str
    user_id: str
    kb_id: str
    file_name: str
    title: str
    chunk_count: int
    status: str
    error_message: str | None = None
    created_at: str
    kb_name: str | None = None
    kb_display_name: str | None = None
    uploader_name: str | None = None
