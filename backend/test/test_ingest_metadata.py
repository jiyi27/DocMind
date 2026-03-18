"""Tests for IngestMetadata required-field validation.

Run with:
    pytest test/test_ingest_metadata.py -v
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docmind.api.schemas import IngestMetadata
from docmind.core.metadata_config import REQUIRED_FIELDS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _full_payload(**overrides) -> dict:
    """Return a complete valid payload, with optional field overrides."""
    base = {
        "title": "测试文档",
        "url": "https://example.com",
        "doc_type": "requirement",
        "service": "risk",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1. 全量合法数据 — 应该成功
# ---------------------------------------------------------------------------


def test_valid_full_payload():
    m = IngestMetadata(**_full_payload())
    assert m.doc_type == "requirement"
    assert m.service == ["risk"]


# ---------------------------------------------------------------------------
# 2. 逗号分隔多值解析
# ---------------------------------------------------------------------------


def test_comma_separated_values():
    m = IngestMetadata(**_full_payload(service="risk,admin"))
    assert m.service == ["risk", "admin"]


# ---------------------------------------------------------------------------
# 3. 必填字段缺失 — 应该报错
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_field", list(REQUIRED_FIELDS))
def test_required_field_missing(missing_field: str):
    """每个必填字段缺失时都应抛出 ValidationError。"""
    payload = _full_payload()
    payload.pop(missing_field)
    with pytest.raises(ValidationError) as exc_info:
        IngestMetadata(**payload)
    errors = exc_info.value.errors()
    messages = " ".join(str(e) for e in errors)
    assert missing_field in messages, (
        f"Expected '{missing_field}' to appear in error messages, got: {messages}"
    )


@pytest.mark.parametrize(
    "empty_value,field",
    [
        ("", "title"),
        ("", "url"),
        ("", "doc_type"),
        ([], "service"),
    ],
)
def test_required_field_empty(empty_value, field: str):
    """必填字段传空值时也应报错（仅当该字段在 REQUIRED_FIELDS 中）。"""
    if field not in REQUIRED_FIELDS:
        pytest.skip(f"'{field}' is not currently required — skipping")
    payload = _full_payload(**{field: empty_value})
    with pytest.raises(ValidationError):
        IngestMetadata(**payload)


# ---------------------------------------------------------------------------
# 4. 非法枚举值 — 应该报错
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "field,bad_value",
    [
        ("doc_type", "unknown_type"),
        ("service", "payments"),
    ],
)
def test_invalid_enum_value(field: str, bad_value: str):
    payload = _full_payload(**{field: bad_value})
    with pytest.raises(ValidationError):
        IngestMetadata(**payload)


# ---------------------------------------------------------------------------
# 5. 可选字段缺失时使用默认值（仅当字段不在 REQUIRED_FIELDS 中）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "optional_field,default",
    [
        ("title", ""),
        ("url", ""),
        ("doc_type", "tech_spec"),
        ("service", ["all"]),
    ],
)
def test_optional_field_uses_default(optional_field: str, default):
    """字段不在 REQUIRED_FIELDS 时，缺省应使用默认值而非报错。"""
    if optional_field in REQUIRED_FIELDS:
        pytest.skip(f"'{optional_field}' is currently required — skipping")
    payload = _full_payload()
    payload.pop(optional_field)
    m = IngestMetadata(**payload)
    assert getattr(m, optional_field) == default
