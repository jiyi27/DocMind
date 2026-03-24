"""Tests for DocumentMetadata and IngestionOptions validation.

Run with:
    pytest test/test_ingest_metadata.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.api.schemas import DocumentMetadata, IngestionOptions


def test_document_metadata_accepts_title_and_url() -> None:
    metadata = DocumentMetadata(title="测试文档", url="https://example.com")
    assert metadata.title == "测试文档"
    assert metadata.url == "https://example.com"


def test_document_metadata_defaults_are_empty_strings() -> None:
    metadata = DocumentMetadata()
    assert metadata.title == ""
    assert metadata.url == ""


def test_ingestion_options_defaults_follow_settings() -> None:
    options = IngestionOptions()
    assert options.retrieval_mode in {"chunk", "full_doc"}
    assert options.chunk_size > 0
    assert options.chunk_overlap >= 0


@pytest.mark.parametrize("mode", ["chunk", "full_doc"])
def test_ingestion_options_accept_valid_retrieval_mode(mode: str) -> None:
    options = IngestionOptions(retrieval_mode=mode)
    assert options.retrieval_mode == mode
