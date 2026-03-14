from __future__ import annotations

from pydantic import BaseModel, Field, field_validator
from typing import Any, Literal

from docmind.core.metadata_config import DEPARTMENTS, DOC_TYPES, SERVICES


class IngestMetadata(BaseModel):
    """Metadata attached to an ingested document.

    Note: business_line is no longer a field here — it is derived automatically
    from the authenticated user's knowledge base (JWT payload).
    """

    title: str = ""
    url: str = ""
    doc_type: str = "tech_spec"

    # Multi-value fields (support comma-separated string input from form data)
    service: list[str] = Field(default_factory=lambda: ["all"])
    department: list[str] = Field(default_factory=lambda: ["all"])

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        if v not in DOC_TYPES:
            raise ValueError(f"doc_type must be one of {DOC_TYPES}, got '{v}'")
        return v

    @field_validator("service", "department", mode="before")
    @classmethod
    def parse_list_field(cls, v: object) -> list[str]:
        """Accept comma-separated string or list from form/JSON input."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v  # type: ignore[return-value]

    @field_validator("service")
    @classmethod
    def validate_service(cls, v: list[str]) -> list[str]:
        invalid = [x for x in v if x not in SERVICES]
        if invalid:
            raise ValueError(f"Invalid service values {invalid}. Allowed: {SERVICES}")
        return v

    @field_validator("department")
    @classmethod
    def validate_department(cls, v: list[str]) -> list[str]:
        invalid = [x for x in v if x not in DEPARTMENTS]
        if invalid:
            raise ValueError(
                f"Invalid department values {invalid}. Allowed: {DEPARTMENTS}"
            )
        return v


class HistoryMessage(BaseModel):
    """A single message in the conversation history passed by the client."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    chat_input: str = Field(..., alias="chatInput", description="The user's question")
    session_id: str = Field(..., alias="sessionId", description="Chat session UUID")
    messages: list[HistoryMessage] = Field(
        default_factory=list,
        alias="messages",
        description="Full conversation history prior to this turn (oldest first)",
    )


class ChatSessionCreate(BaseModel):
    title: str = Field(default="New Conversation")
    kb_id: str | None = None


class ChatMessageCreate(BaseModel):
    role: Literal["user", "assistant"]
    content: str
    sources: list[str] = Field(default_factory=list)
    model_name: str = ""
    token_count: int = 0
