from __future__ import annotations

import sys
from pathlib import Path

from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.ingestion.nodes import split_text_node


def _split_pdf(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int = 0,
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
            "chunk_overlap": chunk_overlap,
        },
    }
    return split_text_node(state)["chunks"]


def test_pdf_paragraphs_split_with_overlap() -> None:
    pdf_text = (
        "Alpha paragraph holds the opening context for the page.\n\n"
        "Beta paragraph should be repeated when overlap is enabled.\n\n"
        "Gamma paragraph closes the sample page."
    )

    chunks = _split_pdf(
        pdf_text,
        chunk_size=130,
        chunk_overlap=70,
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
