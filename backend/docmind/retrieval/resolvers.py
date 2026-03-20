"""Resolver dispatch for retrieval — converts a Qdrant Document into a ContextItem.

Each resolver handles one content source type. Adding a new type means adding a
new resolver here; the retrieval main loop in nodes.py does not need to change.

Dispatch priority:
  1. retrieval_mode == full_doc  →  FullDocResolver  (document-level strategy)
  2. chunk_type == image         →  ImageResolver
  3. chunk_type == code_block    →  CodeBlockResolver
  4. otherwise                   →  TextResolver
"""

from __future__ import annotations

from langchain_core.documents import Document

from docmind.core import logger
from docmind.core.metadata import (
    CHUNK_TYPE_CODE_BLOCK,
    CHUNK_TYPE_IMAGE,
    DEFAULT_RETRIEVAL_MODE,
    META_CHUNK_TYPE,
    META_DOC_ID,
    META_FILE_NAME,
    META_FILE_PATH,
    META_IMAGE_URL,
    META_ORIGINAL_CONTENT,
    META_RETRIEVAL_MODE,
    META_SOURCE,
    META_TITLE,
    META_URL,
    RETRIEVAL_MODE_FULL_DOC,
)
from docmind.ingestion.loaders import load_document
from docmind.retrieval.context import ContextItem


def _build_source_label(index: int, title: str, url: str) -> str:
    if url and title:
        return f"[{index}] [{title}]({url})"
    if url:
        return f"[{index}] [{url}]({url})"
    if title:
        return f"[{index}] {title}"
    return f"[{index}] unknown source"


def _extract_common(index: int, doc: Document) -> tuple[str, str, str]:
    """Return (title, url, source_label) from document metadata."""
    meta = doc.metadata or {}
    title = meta.get(META_TITLE) or meta.get(META_FILE_NAME) or meta.get(META_SOURCE, "")
    url = meta.get(META_URL, "")
    return title, url, _build_source_label(index, title, url)


class TextResolver:
    """Plain text chunk — use page_content directly."""

    def resolve(self, index: int, doc: Document) -> ContextItem:
        title, url, source_label = _extract_common(index, doc)
        return ContextItem(
            index=index,
            chunk_type="text",
            content=doc.page_content,
            title=title,
            url=url,
            source_label=source_label,
        )


class CodeBlockResolver:
    """Chunk containing code blocks — restore original code from metadata.

    During ingestion, code blocks are replaced with LLM summaries in
    page_content so that semantic search works better. original_content
    preserves the raw code to show users the actual source.
    """

    def resolve(self, index: int, doc: Document) -> ContextItem:
        meta = doc.metadata or {}
        title, url, source_label = _extract_common(index, doc)
        content = meta.get(META_ORIGINAL_CONTENT, doc.page_content)
        return ContextItem(
            index=index,
            chunk_type="code",
            content=content,
            title=title,
            url=url,
            source_label=source_label,
        )


class ImageResolver:
    """Image chunk — caption/summary is used as context text; image_url preserved.

    Future: pass image_url directly to a multimodal LLM here instead of
    relying on the ingestion-time caption in page_content.
    """

    def resolve(self, index: int, doc: Document) -> ContextItem:
        meta = doc.metadata or {}
        title, url, source_label = _extract_common(index, doc)
        return ContextItem(
            index=index,
            chunk_type="image",
            content=doc.page_content,
            image_url=meta.get(META_IMAGE_URL),
            title=title,
            url=url,
            source_label=source_label,
        )


class FullDocResolver:
    """Full-document retrieval — load the entire file from disk.

    Future: replace _load_full_text with a MinIO/object-store fetch using
    the same file_path key stored in metadata at ingestion time.
    """

    def resolve(
        self,
        index: int,
        doc: Document,
        *,
        max_full_doc_chars: int,
        seen_full_doc_ids: set[str],
        full_doc_count: int,
        max_full_docs: int,
        kb_name: str,
    ) -> tuple[ContextItem | None, int]:
        """Return (item, updated_count). Returns (None, count) when skipped."""
        meta = doc.metadata or {}
        doc_id = meta.get(META_DOC_ID, "")

        if doc_id in seen_full_doc_ids:
            return None, full_doc_count
        if full_doc_count >= max_full_docs:
            return None, full_doc_count

        file_path = meta.get(META_FILE_PATH, "")
        if not file_path:
            logger.warning(
                "full_doc_missing_file_path",
                {"doc_id": doc_id, "kb_name": kb_name},
            )
            return None, full_doc_count

        try:
            docs = load_document(file_path)
            full_text = "\n\n".join(d.page_content for d in docs)
        except Exception as exc:
            logger.warning(
                "full_doc_load_failed",
                {"doc_id": doc_id, "file_path": file_path, "error": str(exc)},
            )
            return None, full_doc_count

        if len(full_text) > max_full_doc_chars:
            full_text = full_text[:max_full_doc_chars]

        seen_full_doc_ids.add(doc_id)
        title, url, source_label = _extract_common(index, doc)
        return (
            ContextItem(
                index=index,
                chunk_type="full_doc",
                content=full_text,
                title=title,
                url=url,
                source_label=source_label,
            ),
            full_doc_count + 1,
        )


_text_resolver = TextResolver()
_code_block_resolver = CodeBlockResolver()
_image_resolver = ImageResolver()
_full_doc_resolver = FullDocResolver()


def get_resolver(meta: dict) -> TextResolver | CodeBlockResolver | ImageResolver | FullDocResolver:
    """Select the appropriate resolver based on document metadata."""
    if meta.get(META_RETRIEVAL_MODE, DEFAULT_RETRIEVAL_MODE) == RETRIEVAL_MODE_FULL_DOC:
        return _full_doc_resolver
    chunk_type = meta.get(META_CHUNK_TYPE, "")
    if chunk_type == CHUNK_TYPE_IMAGE:
        return _image_resolver
    if chunk_type == CHUNK_TYPE_CODE_BLOCK:
        return _code_block_resolver
    return _text_resolver
