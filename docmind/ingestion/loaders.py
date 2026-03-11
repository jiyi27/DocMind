"""Document loaders — PDF and Markdown."""

from __future__ import annotations

from pathlib import Path

from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader


def load_pdf(file_path: str | Path) -> list[Document]:
    """Load a PDF file and return a list of Documents (one per page)."""
    loader = PyPDFLoader(str(file_path))
    return loader.load()


def load_markdown(file_path: str | Path) -> list[Document]:
    """Load a Markdown file and return it as a single Document."""
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    return [
        Document(
            page_content=content,
            metadata={"source": str(path), "file_name": path.name},
        )
    ]


def load_document(file_path: str | Path) -> list[Document]:
    """Auto-detect file type and load accordingly.

    Supported: .pdf, .md
    Raises ValueError for unsupported types.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    loaders = {
        ".pdf": load_pdf,
        ".md": load_markdown,
    }

    loader_fn = loaders.get(suffix)
    if loader_fn is None:
        raise ValueError(f"Unsupported file type: {suffix}. Supported: {list(loaders.keys())}")

    return loader_fn(path)
