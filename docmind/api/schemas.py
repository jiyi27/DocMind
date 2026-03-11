from __future__ import annotations

from pydantic import BaseModel, Field

class IngestMetadata(BaseModel):
    """Optional metadata attached to an ingested document."""

    title: str = ""
    url: str = ""
    category: str = "none"
    business_line: str = "none"
    audience: str = "all"

class IngestResponse(BaseModel):
    status: str
    chunk_count: int
    file_name: str

class ChatRequest(BaseModel):
    chat_input: str = Field(..., alias="chatInput", description="The user's question")
    session_id: str = Field(default="default", alias="sessionId")


class ChatResponse(BaseModel):
    answer: str
    sources: list[str] = []
    session_id: str
