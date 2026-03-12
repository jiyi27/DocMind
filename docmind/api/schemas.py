from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Any

from docmind.core.metadata_config import BUSINESS_LINES, DEPARTMENTS, DOC_TYPES, REQUIRED_FIELDS, SERVICES


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

    @model_validator(mode="before")
    @classmethod
    def check_required_fields(cls, values: Any) -> Any:
        """根据 metadata_config.REQUIRED_FIELDS 动态校验必填字段。"""
        # 单值字段：值为空字符串视为未填
        _SINGLE = {"title", "url", "doc_type"}
        # 多值字段：值为空列表视为未填
        _MULTI = {"business_line", "service", "department"}

        missing = []
        for field in REQUIRED_FIELDS:
            val = values.get(field) if isinstance(values, dict) else getattr(values, field, None)
            if field in _SINGLE and not val:
                missing.append(field)
            elif field in _MULTI and not val:
                missing.append(field)
        if missing:
            raise ValueError(f"Missing required metadata fields: {missing}")
        return values

class ChatRequest(BaseModel):
    chat_input: str = Field(..., alias="chatInput", description="The user's question")
    session_id: str = Field(default="default", alias="sessionId")
