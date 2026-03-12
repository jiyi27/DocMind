from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from docmind.core.metadata_config import BUSINESS_LINES, DEPARTMENTS, DOC_TYPES, SERVICES


class IngestMetadata(BaseModel):
    """Optional metadata attached to an ingested document."""

    title: str = ""
    url: str = ""

    # Single-value field
    doc_type: str = "tech_spec"

    # Multi-value fields (support comma-separated string input from form data)
    business_line: list[str] = Field(default_factory=lambda: ["all"])
    service: list[str] = Field(default_factory=lambda: ["all"])
    department: list[str] = Field(default_factory=lambda: ["all"])

    @field_validator("doc_type")
    @classmethod
    def validate_doc_type(cls, v: str) -> str:
        if v not in DOC_TYPES:
            raise ValueError(f"doc_type must be one of {DOC_TYPES}, got '{v}'")
        return v

    @field_validator("business_line", "service", "department", mode="before")
    @classmethod
    def parse_list_field(cls, v: object) -> list[str]:
        """Accept comma-separated string or list from form/JSON input."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v  # type: ignore[return-value]

    @field_validator("business_line")
    @classmethod
    def validate_business_line(cls, v: list[str]) -> list[str]:
        invalid = [x for x in v if x not in BUSINESS_LINES]
        if invalid:
            raise ValueError(f"Invalid business_line values {invalid}. Allowed: {BUSINESS_LINES}")
        return v

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
            raise ValueError(f"Invalid department values {invalid}. Allowed: {DEPARTMENTS}")
        return v

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
