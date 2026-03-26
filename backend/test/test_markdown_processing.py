from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.core.metadata import (  # noqa: E402
    CHUNK_TYPE_CODE_BLOCK,
    CHUNK_TYPE_TEXT,
    META_CODE_LANGUAGE,
    META_ORIGINAL_CONTENT,
)
from docmind.ingestion import nodes as ingestion_nodes  # noqa: E402
from docmind.ingestion.nodes import (  # noqa: E402
    _halve_text,
    _protect_fenced_blocks,
    _table_to_prose,
    load_document_node,
    split_text_node,
    summarize_code_node,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _read_fixture(name: str) -> str:
    return (FIXTURE_DIR / name).read_text(encoding="utf-8")


def _build_markdown_state(
    text: str,
    *,
    title: str = "DocMind Guide",
    file_name: str = "sample.md",
    chunk_size: int = 160,
    chunk_overlap: int = 0,
) -> dict:
    return {
        "documents": [
            Document(
                page_content=text,
                metadata={"file_name": file_name, "title": title},
            )
        ],
        "doc_id": "doc-123",
        "user_id": "user-456",
        "kb_name": "kb-demo",
        "options": {
            "retrieval_mode": "chunk",
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
    }


def _split_markdown(
    fixture_name: str,
    *,
    chunk_size: int,
    chunk_overlap: int = 0,
) -> list[Document]:
    state = _build_markdown_state(
        _read_fixture(fixture_name),
        file_name=fixture_name,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )
    return split_text_node(state)["chunks"]


class TestMarkdownFlow:
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

    def test_language_code_block_becomes_dedicated_code_chunk(self) -> None:
        chunks = _split_markdown("atomic_blocks.md", chunk_size=120)

        code_chunks = [
            chunk
            for chunk in chunks
            if chunk.metadata.get("chunk_type") == CHUNK_TYPE_CODE_BLOCK
        ]
        quote_chunks = [
            chunk
            for chunk in chunks
            if "Quoted guidance should stay together." in chunk.page_content
        ]
        table_chunks = [
            chunk for chunk in chunks if "Feature: Search" in chunk.page_content
        ]

        assert len(code_chunks) == 1
        assert code_chunks[0].metadata["chunk_type"] == CHUNK_TYPE_CODE_BLOCK
        assert code_chunks[0].metadata[META_CODE_LANGUAGE] == "python"
        assert "```python" in code_chunks[0].page_content
        assert "return message.upper()" in code_chunks[0].page_content
        assert code_chunks[0].page_content.count("```") == 2
        assert "DocMind Guide / Reference" not in code_chunks[0].page_content

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

    def test_plain_fenced_block_is_restored_as_text_without_fences(self) -> None:
        chunks = split_text_node(
            _build_markdown_state(
                (
                    "# Notes\n\n"
                    "Intro text before sample.\n\n"
                    "```\n"
                    "line one\n"
                    "line two\n"
                    "```\n\n"
                    "Closing paragraph."
                ),
                file_name="plain_fence.md",
                chunk_size=200,
            )
        )["chunks"]

        assert len(chunks) == 1
        assert chunks[0].metadata.get("chunk_type", CHUNK_TYPE_TEXT) == CHUNK_TYPE_TEXT
        assert "```" not in chunks[0].page_content
        assert "line one\nline two" in chunks[0].page_content

    def test_oversized_language_code_block_splits_into_multiple_code_chunks(
        self,
    ) -> None:
        code_lines = "\n".join(
            f'print("line {idx} with enough content to force splitting")'
            for idx in range(1, 9)
        )
        chunks = split_text_node(
            _build_markdown_state(
                f"# Code\n\n```python\n{code_lines}\n```",
                file_name="oversized_code.md",
                chunk_size=120,
            )
        )["chunks"]

        code_chunks = [
            chunk
            for chunk in chunks
            if chunk.metadata.get("chunk_type") == CHUNK_TYPE_CODE_BLOCK
        ]

        assert len(code_chunks) >= 2
        assert all(
            chunk.page_content.startswith("```python\n") for chunk in code_chunks
        )
        assert all(chunk.page_content.endswith("\n```") for chunk in code_chunks)
        assert {chunk.metadata["code_part_count"] for chunk in code_chunks} == {
            len(code_chunks)
        }
        assert [chunk.metadata["code_part_index"] for chunk in code_chunks] == list(
            range(1, len(code_chunks) + 1)
        )

    def test_oversized_markdown_block_is_split_instead_of_failing(self) -> None:
        chunks = _split_markdown(
            "oversized_block.md",
            chunk_size=120,
        )

        assert len(chunks) >= 3
        assert all(chunk.page_content.strip() for chunk in chunks)
        assert any(
            "This paragraph is intentionally long" in chunk.page_content
            for chunk in chunks
        )

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
            "chunk_overlap": 0,
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


class TestMarkdownHelpers:
    def test_protect_fenced_blocks_replaces_each_fenced_block_with_placeholders(
        self,
    ) -> None:
        text = (
            "# Title\n\n"
            "Before code block.\n\n"
            "```python\n"
            "print('hello')\n"
            "```\n\n"
            "Between blocks.\n\n"
            "```sql\n"
            "SELECT 1;\n"
            "```\n\n"
            "After code block.\n"
        )

        protected_text, fenced_blocks = _protect_fenced_blocks(text)

        assert "__CODE_BLOCK_0__" in protected_text
        assert "__CODE_BLOCK_1__" in protected_text
        assert "```python" not in protected_text
        assert "```sql" not in protected_text
        assert fenced_blocks == [
            {
                "raw": "```python\nprint('hello')\n```",
                "language": "python",
                "content": "print('hello')",
                "is_language_fenced": True,
            },
            {
                "raw": "```sql\nSELECT 1;\n```",
                "language": "sql",
                "content": "SELECT 1;",
                "is_language_fenced": True,
            },
        ]

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


class _FakeCodeChain:
    def invoke(self, payload: dict) -> SimpleNamespace:
        return SimpleNamespace(
            content=f"summary for {payload['language']} in {payload['headers']}"
        )


class _FakeCodePrompt:
    def __or__(self, _llm: object) -> _FakeCodeChain:
        return _FakeCodeChain()


class TestSummarizeCodeNode:
    def test_summarize_code_node_only_summarizes_dedicated_code_chunks(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        long_code = "\n".join(
            f'print("line {idx} with enough code content for summarization")'
            for idx in range(1, 10)
        )
        chunks = split_text_node(
            _build_markdown_state(
                (
                    "# API\n\n"
                    "Lead paragraph before code.\n\n"
                    f"```python\n{long_code}\n```\n\n"
                    "Trailing explanation."
                ),
                file_name="summarize_code.md",
                chunk_size=1200,
            )
        )["chunks"]

        monkeypatch.setattr(
            ingestion_nodes, "code_summarization_prompt", _FakeCodePrompt()
        )
        monkeypatch.setattr(ingestion_nodes, "get_llm", lambda: object())
        monkeypatch.setattr(
            ingestion_nodes,
            "settings",
            SimpleNamespace(ingestion=SimpleNamespace(enable_code_summarization=True)),
        )

        processed = summarize_code_node({"chunks": chunks})["chunks"]
        code_chunks = [
            chunk
            for chunk in processed
            if chunk.metadata.get("chunk_type") == CHUNK_TYPE_CODE_BLOCK
        ]
        text_chunks = [
            chunk
            for chunk in processed
            if chunk.metadata.get("chunk_type", CHUNK_TYPE_TEXT) == CHUNK_TYPE_TEXT
        ]

        assert len(code_chunks) == 1
        assert code_chunks[0].page_content.startswith("summary for python")
        assert code_chunks[0].metadata[META_ORIGINAL_CONTENT].startswith("```python\n")
        assert "Lead paragraph before code." in text_chunks[0].page_content
        assert "Trailing explanation." in text_chunks[-1].page_content
