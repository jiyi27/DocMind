"""Document loaders — PDF and Markdown."""

from __future__ import annotations

from pathlib import Path

import pymupdf4llm
from langchain_core.documents import Document

from docmind.core import logger
from docmind.core.exceptions import DocumentError

# Re-export under legacy names so existing raise sites keep working.
DocumentLoadError = DocumentError
UnsupportedFileTypeError = DocumentError


_PDF_MIN_TEXT_LENGTH = 50  # non-whitespace characters


def load_pdf(file_path: str | Path) -> list[Document]:
    """Load a PDF file and return a single Markdown Document via pymupdf4llm.

    pymupdf4llm reads the PDF's internal text layer and font metadata to infer
    heading levels, producing structured Markdown that the downstream splitter
    can handle properly.

    Scanned / image-only PDFs have no text layer — pymupdf4llm returns an
    empty or near-empty string for them. We detect this early and raise a
    user-facing DocumentError rather than silently producing empty chunks.

    Raises
    ------
    DocumentLoadError
        If the PDF is corrupted, cannot be parsed, or contains no extractable
        text (e.g. scanned / image-based PDF).
    """
    path = Path(file_path)
    try:
        md_text = pymupdf4llm.to_markdown(str(path))

        if len(md_text.replace(" ", "").replace("\n", "")) < _PDF_MIN_TEXT_LENGTH:
            raise DocumentError(
                "无法提取文本：该 PDF 可能是扫描件或图片型文档，暂不支持。"
                "请转换为可复制文字的 PDF 后重新上传。"
            )

        logger.debug(
            "loader_pdf_success",
            {"file_path": str(path), "content_length": len(md_text)},
        )
        return [
            Document(
                page_content=md_text,
                metadata={"source": str(path), "file_name": path.name},
            )
        ]
    except DocumentError:
        raise
    except Exception as exc:
        logger.error(
            "loader_pdf_failed",
            {
                "file_path": str(path),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise DocumentError(f"Failed to load PDF '{file_path}': {exc}") from exc


def load_markdown(file_path: str | Path) -> list[Document]:
    """Load a Markdown file and return it as a single Document.

    Unlike PDF, the entire file is treated as one Document regardless of length.
    Returns a list for interface consistency with load_pdf.

    Raises
    ------
    DocumentLoadError
        If the file cannot be read.
    """
    path = Path(file_path)
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.error(
            "loader_markdown_failed",
            {
                "file_path": str(file_path),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise DocumentError(
            f"Failed to read Markdown file '{file_path}': {exc}"
        ) from exc

    logger.debug(
        "loader_markdown_success",
        {
            "file_path": str(file_path),
            "content_length": len(content),
        },
    )
    return [
        Document(
            page_content=content,
            metadata={"source": str(path), "file_name": path.name},
        )
    ]


def load_document(file_path: str | Path) -> list[Document]:
    """Auto-detect file type and load accordingly.

    Supported: .pdf, .md

    Raises
    ------
    UnsupportedFileTypeError
        If the file extension is not supported (should map to HTTP 400).
    DocumentLoadError
        If the file exists but cannot be parsed.
    """
    path = Path(file_path)
    suffix = path.suffix.lower()

    loaders = {
        ".pdf": load_pdf,
        ".md": load_markdown,
    }

    loader_fn = loaders.get(suffix)
    if loader_fn is None:
        logger.error(
            "loader_unsupported_type",
            {
                "file_path": str(file_path),
                "suffix": suffix,
                "supported": list(loaders.keys()),
            },
        )
        raise DocumentError(
            f"Unsupported file type '{suffix}'. Supported types: {list(loaders.keys())}"
        )

    return loader_fn(path)
