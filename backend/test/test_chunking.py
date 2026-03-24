from __future__ import annotations

import sys
from pathlib import Path

import pytest
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.ingestion import nodes as ingestion_nodes
from docmind.ingestion.nodes import (
    _halve_text,
    _table_to_prose,
    load_document_node,
    split_text_node,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _split_markdown(
    fixture_name: str,
    *,
    chunk_size: int,
    max_chunk_size: int = 240,
    chunk_overlap: int = 0,
    strict_mode: bool = True,
) -> list[Document]:
    state = {
        "documents": [
            Document(
                page_content=_read_fixture(fixture_name),
                metadata={"file_name": fixture_name, "title": "DocMind Guide"},
            )
        ],
        "doc_id": "doc-123",
        "user_id": "user-456",
        "kb_name": "kb-demo",
        "options": {
            "retrieval_mode": "chunk",
            "chunk_size": chunk_size,
            "max_chunk_size": max_chunk_size,
            "chunk_overlap": chunk_overlap,
            "strict_mode": strict_mode,
        },
    }
    return split_text_node(state)["chunks"]


def _split_pdf(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int = 0,
    max_chunk_size: int = 240,
    strict_mode: bool = True,
) -> list[Document]:
    state = {
        "documents": [
            Document(
                page_content=text,
                metadata={"file_name": "sample.pdf", "title": "PDF Guide"},
            )
        ],
        "doc_id": "doc-123",
        "user_id": "user-456",
        "kb_name": "kb-demo",
        "options": {
            "retrieval_mode": "chunk",
            "chunk_size": chunk_size,
            "max_chunk_size": max_chunk_size,
            "chunk_overlap": chunk_overlap,
            "strict_mode": strict_mode,
        },
    }
    return split_text_node(state)["chunks"]


class TestMarkdownSplitting:
    def test_headers_create_new_chunks_and_add_breadcrumbs(self) -> None:
        chunks = _split_markdown("basic_headers.md", chunk_size=160)
        breadcrumbs = [chunk.page_content.split("\n\n", 1)[0] for chunk in chunks]

        assert len(chunks) >= 3
        assert breadcrumbs[0] == "DocMind Guide / Getting Started"
        assert "DocMind Guide / Getting Started / Installation" in breadcrumbs
        assert "DocMind Guide / Getting Started / Usage" in breadcrumbs

        assert chunks[0].metadata["header_1"] == "Getting Started"
        assert any(chunk.metadata.get("header_2") == "Installation" for chunk in chunks)
        assert any(chunk.metadata.get("header_2") == "Usage" for chunk in chunks)

    def test_overlap_can_be_controlled_from_state(self) -> None:
        chunks_without_overlap = _split_markdown(
            "basic_headers.md",
            chunk_size=260,
            chunk_overlap=0,
        )
        chunks_with_overlap = _split_markdown(
            "basic_headers.md",
            chunk_size=260,
            chunk_overlap=130,
        )

        assert len(chunks_without_overlap) == len(chunks_with_overlap)
        assert all(
            "Beta overlap paragraph keeps enough trailing context"
            not in chunk.page_content
            for chunk in chunks_without_overlap[1:]
        )
        assert (
            "Beta overlap paragraph keeps enough trailing context"
            in chunks_with_overlap[1].page_content
        )


class TestAtomicBlocks:
    def test_code_block_blockquote_and_table_remain_atomic(self) -> None:
        chunks = _split_markdown("atomic_blocks.md", chunk_size=120)

        code_chunks = [chunk for chunk in chunks if "def greet" in chunk.page_content]
        quote_chunks = [
            chunk
            for chunk in chunks
            if "Quoted guidance should stay together." in chunk.page_content
        ]
        table_chunks = [
            chunk for chunk in chunks if "Feature: Search" in chunk.page_content
        ]

        assert len(code_chunks) == 1
        assert "```python" in code_chunks[0].page_content
        assert "return message.upper()" in code_chunks[0].page_content
        assert code_chunks[0].page_content.count("```") == 2

        assert len(quote_chunks) == 1
        assert "> Quoted guidance" not in quote_chunks[0].page_content
        assert (
            "The markdown marker should be removed in the final chunk."
            in quote_chunks[0].page_content
        )

        assert len(table_chunks) == 1
        assert "| Feature | Value |" not in table_chunks[0].page_content
        assert "Feature: Search, Value: Enabled" in table_chunks[0].page_content
        assert "Feature: Chunk Size, Value: 400" in table_chunks[0].page_content


class TestStrictMode:
    def test_oversized_markdown_block_raises(self) -> None:
        with pytest.raises(ValueError, match="Strict mode validation failed"):
            _split_markdown(
                "oversized_block.md",
                chunk_size=120,
                max_chunk_size=140,
                strict_mode=True,
            )


class TestNonStrictMode:
    def test_oversized_markdown_block_is_split_instead_of_failing(self) -> None:
        chunks = _split_markdown(
            "oversized_block.md",
            chunk_size=120,
            max_chunk_size=140,
            strict_mode=False,
        )

        assert len(chunks) >= 3
        assert all(chunk.page_content.strip() for chunk in chunks)
        assert any(
            "This paragraph is intentionally long" in chunk.page_content
            for chunk in chunks
        )


class TestPdfSplitting:
    def test_pdf_paragraphs_split_with_overlap(self) -> None:
        pdf_text = (
            "Alpha paragraph holds the opening context for the page.\n\n"
            "Beta paragraph should be repeated when overlap is enabled.\n\n"
            "Gamma paragraph closes the sample page."
        )

        chunks = _split_pdf(
            pdf_text,
            chunk_size=130,
            chunk_overlap=70,
            strict_mode=True,
        )

        assert len(chunks) == 2
        assert (
            "Beta paragraph should be repeated when overlap is enabled."
            in chunks[0].page_content
        )
        assert (
            "Beta paragraph should be repeated when overlap is enabled."
            in chunks[1].page_content
        )
        assert "Gamma paragraph closes the sample page." in chunks[1].page_content


class TestMetadataInheritance:
    def test_load_then_split_preserves_identity_metadata(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        doc = Document(
            page_content=_read_fixture("basic_headers.md"),
            metadata={"file_name": "basic_headers.md", "title": "DocMind Guide"},
        )
        state = {
            "file_path": "fixtures/basic_headers.md",
            "metadata": {"source": "fixture"},
            "doc_id": "doc-123",
            "user_id": "user-456",
            "kb_name": "kb-demo",
            "retrieval_mode": "chunk",
            "chunk_size": 160,
            "max_chunk_size": 240,
            "chunk_overlap": 0,
            "strict_mode": True,
        }

        monkeypatch.setattr(ingestion_nodes, "load_document", lambda _: [doc])
        loaded = load_document_node(state)
        chunks = split_text_node({**state, **loaded})["chunks"]

        assert chunks
        for chunk in chunks:
            assert chunk.metadata["doc_id"] == "doc-123"
            assert chunk.metadata["user_id"] == "user-456"
            assert chunk.metadata["kb_name"] == "kb-demo"
            assert chunk.metadata["retrieval_mode"] == "chunk"
            assert chunk.metadata["source"] == "fixture"


class TestPureFunctions:
    def test_halve_text_prefers_newline_and_respects_max_size(self) -> None:
        text = (
            "first section keeps context before the split point\n"
            "second section is long enough to force recursion and should stay within bounds\n"
            "third section closes the example"
        )

        pieces = _halve_text(text, max_size=60)

        assert len(pieces) >= 3
        assert all(len(piece) <= 60 for piece in pieces)
        assert any(piece.startswith("second section") for piece in pieces)

    def test_table_to_prose_converts_standard_tables_only(self) -> None:
        standard_table = (
            "| Name | Value |\n| --- | --- |\n| chunk_size | 400 |\n| overlap | 80 |\n"
        )
        non_standard_table = "| only one row |\n| still not a standard table |"

        assert _table_to_prose(standard_table) == (
            "Name: chunk_size, Value: 400\nName: overlap, Value: 80"
        )
        assert _table_to_prose(non_standard_table) == non_standard_table
