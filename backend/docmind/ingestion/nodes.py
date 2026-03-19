"""Ingestion graph nodes — each function is a LangGraph node."""

from __future__ import annotations

import re
from typing import Callable

from langchain_core.documents import Document

from docmind.core.config import settings
from docmind.core import logger
from docmind.core.llm import get_llm
from docmind.ingestion.constants import DEFAULT_RETRIEVAL_MODE, DEFAULT_STRICT_MODE
from docmind.ingestion.loaders import load_document
from docmind.ingestion.state import IngestionState
from docmind.ingestion.prompts import code_summarization_prompt
from docmind.vectorstore.qdrant_store import get_vector_store_for_kb

FENCED_BLOCK_PATTERN = re.compile(r"```.*?```", flags=re.DOTALL)


def _halve_text(text: str, max_size: int) -> list[str]:
    """Recursively halve *text* until every piece is ≤ *max_size* chars.

    Prefers splitting at a natural newline near the midpoint (±100 chars).
    Falls back to a hard character split when no newline is available.
    """
    if len(text) <= max_size:
        return [text]
    mid = len(text) // 2
    split_pos = text.rfind("\n", max(0, mid - 100), mid + 100)
    if split_pos == -1:
        split_pos = mid
    result = []
    for part in (text[:split_pos].strip(), text[split_pos:].strip()):
        if part:
            result.extend(_halve_text(part, max_size))
    return result


def _collect_overlap_blocks(blocks: list[str], overlap: int) -> tuple[list[str], int]:
    """Return trailing blocks that fit within the *overlap* character budget.

    Iterates *blocks* in reverse, accumulating until the budget is exhausted.
    The returned list is in original (forward) order.
    """
    if overlap <= 0 or len(blocks) <= 1:
        return [], 0
    kept_reversed: list[str] = []
    kept_len = 0
    for blk in reversed(blocks):
        sep = 2 if kept_reversed else 0
        if kept_len + sep + len(blk) > overlap:
            break
        kept_reversed.append(blk)
        kept_len += sep + len(blk)
    return list(reversed(kept_reversed)), kept_len


# (?P<language>[a-zA-Z0-9_+-]+) and (?P<content>.*?): Named Capturing Group
# Assigns a unique label to the captured sub-pattern,
# allowing for retrieval via the variable name rather than a numeric index.
LANGUAGE_FENCED_BLOCK_PATTERN = re.compile(
    r"```(?P<language>[a-zA-Z0-9_+-]+)[ \t]*\n(?P<content>.*?)```",
    flags=re.DOTALL,
)
BLOCKQUOTE_PATTERN = re.compile(r"(?:^[ \t]*>[ \t]?.*\n?)+", flags=re.MULTILINE)
TABLE_PATTERN = re.compile(r"(?:^[ \t]*\|.+\|[ \t]*\n)+", flags=re.MULTILINE)


def load_document_node(state: IngestionState) -> dict:
    """Load documents from the given file path.

    PDF → one Document per page; Markdown → one Document for the whole file.
    User-supplied metadata (title, doc_type, service, etc.) is stamped onto
    every Document here so all downstream chunks inherit it automatically.
    """
    file_path = state["file_path"]

    try:
        docs = load_document(file_path)
    except Exception as exc:
        logger.error(
            "ingest_load_failed",
            {
                "file_path": file_path,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    # Stamp user-provided metadata + identity fields onto every Document so
    # that all chunks produced in the next step inherit them.
    metadata = state.get("metadata", {})
    doc_id = state.get("doc_id", "")
    user_id = state.get("user_id", "")
    kb_name = state.get("kb_name", "")
    retrieval_mode = state.get("retrieval_mode", DEFAULT_RETRIEVAL_MODE)
    file_path = state.get("file_path", "")
    for doc in docs:
        doc.metadata.update(metadata)
        doc.metadata["doc_id"] = doc_id
        doc.metadata["user_id"] = user_id
        doc.metadata["kb_name"] = kb_name
        doc.metadata["retrieval_mode"] = retrieval_mode
        # Stored so retrieve_node can re-read the full file for full_doc mode.
        if retrieval_mode == "full_doc":
            doc.metadata["file_path"] = file_path

    return {"documents": docs}


def _protect_fenced_blocks(text: str) -> tuple[str, list[str]]:
    """Replace fenced blocks with placeholders so they stay atomic during splitting."""
    fenced_blocks: list[str] = []

    def replacer(match: re.Match[str]) -> str:
        fenced_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(fenced_blocks) - 1}__"

    text_without_fenced_blocks = FENCED_BLOCK_PATTERN.sub(replacer, text)
    return text_without_fenced_blocks, fenced_blocks


def _restore_fenced_block_placeholders(text: str, fenced_blocks: list[str]) -> str:
    """Swap placeholder tokens back to their original fenced block content."""

    def restore(match: re.Match[str]) -> str:
        return fenced_blocks[int(match.group(1))]

    return re.sub(r"__CODE_BLOCK_(\d+)__", restore, text)


def _protect_blockquotes(text: str) -> tuple[str, list[str]]:
    """Replace contiguous blockquote regions with placeholders so they stay atomic.

    The '>' prefix is stripped from each line so the restored text is clean prose
    without Markdown syntax noise.
    """
    blocks: list[str] = []

    def replacer(m: re.Match[str]) -> str:
        clean_lines = [
            re.sub(r"^[ \t]*>[ \t]?", "", line) for line in m.group(0).splitlines()
        ]
        blocks.append("\n".join(clean_lines).strip())
        return f"\n\n__BLOCKQUOTE_{len(blocks) - 1}__\n\n"

    return BLOCKQUOTE_PATTERN.sub(replacer, text), blocks


def _restore_blockquote_placeholders(text: str, blocks: list[str]) -> str:
    return re.sub(r"__BLOCKQUOTE_(\d+)__", lambda m: blocks[int(m.group(1))], text)


def _table_to_prose(raw_table: str) -> str:
    """Convert a Markdown pipe table to readable 'key: value' lines.

    If the table doesn't match the standard header-separator-data layout,
    the original text is returned unchanged.
    """
    lines = [line.strip() for line in raw_table.strip().splitlines() if line.strip()]
    sep_idx = next(
        (i for i, line in enumerate(lines) if re.match(r"^\|[-| :]+\|$", line)),
        None,
    )
    if sep_idx is None or sep_idx == 0:
        return raw_table

    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[sep_idx + 1 :]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        pairs = ", ".join(f"{h}: {c}" for h, c in zip(headers, cells) if c)
        if pairs:
            rows.append(pairs)
    return "\n".join(rows)


def _protect_tables(text: str) -> tuple[str, list[str]]:
    """Replace pipe tables with placeholders, storing converted prose."""
    blocks: list[str] = []

    def replacer(m: re.Match[str]) -> str:
        blocks.append(_table_to_prose(m.group(0)))
        return f"\n\n__TABLE_{len(blocks) - 1}__\n\n"

    return TABLE_PATTERN.sub(replacer, text), blocks


def _restore_table_placeholders(text: str, blocks: list[str]) -> str:
    return re.sub(r"__TABLE_(\d+)__", lambda m: blocks[int(m.group(1))], text)


def _iter_language_fenced_blocks(text: str) -> list[re.Match[str]]:
    """Return only fenced blocks that declare a language after opening backticks."""
    # finditer 是“迭代匹配”：它会在文本中不断搜索直到没有更多匹配项，
    # 相比 findall，它保留了匹配结果的完整内部状态（如起始索引、结束索引、命名捕获组数据）
    return list(LANGUAGE_FENCED_BLOCK_PATTERN.finditer(text))


def _custom_split_markdown(
    doc: Document, target_size: int, max_size: int, overlap: int, strict: bool
) -> list[Document]:
    """Strictly split Markdown respecting headers, code blocks, blockquotes, tables, and paragraphs.

    Processing order:
      1. Protect fenced code blocks  (they contain blank lines that would confuse paragraph splitting)
      2. Protect blockquotes         (strip '>' prefix noise; keep multi-paragraph quotes atomic)
      3. Protect tables              (convert pipe syntax to 'key: value' prose; keep tables atomic)
      4. Split on blank lines → raw blocks
      5. Dispatch each block to a typed handler via a lookup table
      6. Restore all placeholders in the final chunks
    """
    text = doc.page_content
    base_meta = doc.metadata.copy()

    # 1–3. Protect atomic structures before paragraph splitting
    text, code_blocks = _protect_fenced_blocks(text)
    text, bq_blocks = _protect_blockquotes(text)
    text, table_blocks = _protect_tables(text)

    # --- Helpers (restore, breadcrumb, overlap) ---

    def _restore_all(s: str) -> str:
        """Swap all placeholders back to their original content in one pass."""
        s = _restore_fenced_block_placeholders(s, code_blocks)
        s = _restore_blockquote_placeholders(s, bq_blocks)
        s = _restore_table_placeholders(s, table_blocks)
        return s

    def build_breadcrumb(headers: dict) -> str:
        """Plain-text breadcrumb from title + current header path.

        e.g. "API Guide / Intro / Background"
        Makes every chunk self-contained for retrieval without Markdown symbols.
        """
        parts = []
        doc_title = base_meta.get("title", "").strip()
        if doc_title:
            parts.append(doc_title)
        parts += [
            headers[f"header_{lvl}"]
            for lvl in sorted(int(k.split("_")[1]) for k in headers)
        ]
        return " / ".join(parts)

    # --- Chunk accumulator state ---
    # current_texts / current_len track the blocks being packed into the next chunk.
    # flush_chunk() seals the current chunk and seeds the next one with overlap blocks.
    docs: list[Document] = []
    current_texts: list[str] = []
    current_len = 0
    current_headers: dict[str, str] = {}

    def flush_chunk() -> None:
        nonlocal current_texts, current_len
        if not current_texts:
            return
        body = "\n\n".join(current_texts)
        breadcrumb = build_breadcrumb(current_headers)
        merged = f"{breadcrumb}\n\n{body}" if breadcrumb else body
        meta = base_meta.copy()
        meta.update(current_headers)
        docs.append(Document(page_content=merged, metadata=meta))
        current_texts, current_len = _collect_overlap_blocks(current_texts, overlap)

    def _pack(text: str) -> None:
        """Append a single already-validated/restored text block into the current chunk."""
        nonlocal current_len
        n = len(text)
        if current_len > 0 and current_len + n + 2 > target_size:
            flush_chunk()
        current_texts.append(text)
        current_len += n + (2 if len(current_texts) > 1 else 0)

    def append_content_block(block: str) -> None:
        restored = _restore_all(block)
        block_len = len(restored)
        if strict:
            if block_len > max_size:
                snippet = restored[:50].replace("\n", " ") + "..."
                raise ValueError(
                    f"Strict mode validation failed: a semantic block exceeds the max length "
                    f"of {max_size} chars (actual: {block_len}). Snippet: '{snippet}'"
                )
            _pack(restored)
        else:
            pieces = (
                _halve_text(restored, target_size)
                if block_len > target_size
                else [restored]
            )
            for piece in pieces:
                _pack(piece)

    # --- 4. Block classifier + typed handlers ---
    _HEADER_RE = re.compile(r"^(#{1,6})\s+(.*)")
    _IMAGE_RE = re.compile(r"^!\[.*?\]\(.*?\)\s*$")

    def _handle_header(block: str) -> None:
        h_match = _HEADER_RE.match(block)
        assert h_match
        level = len(h_match.group(1))
        flush_chunk()
        for k in [k for k in current_headers if int(k.split("_")[1]) >= level]:
            del current_headers[k]
        current_headers[f"header_{level}"] = h_match.group(2).strip()

    def _handle_image(block: str) -> None:
        # TODO: implement image processing (OCR or multimodal model)
        pass

    def _handle_content(block: str) -> None:
        # Regular paragraph / prose block — pack into the current chunk.
        append_content_block(block)

    def classify(block: str) -> str:
        if _HEADER_RE.match(block):
            return "header"
        if _IMAGE_RE.match(block):
            return "image"
        return "content"

    HANDLERS: dict[str, Callable[[str], None]] = {
        "header": _handle_header,
        "image": _handle_image,
        "content": _handle_content,
    }

    # --- 5. Dispatch each paragraph-level block to its handler ---
    raw_blocks = [b.strip() for b in text.split("\n\n") if b.strip()]
    for block in raw_blocks:
        HANDLERS[classify(block)](block)

    # --- 6. Seal the final in-progress chunk ---
    flush_chunk()
    return docs


def _split_pdf(
    doc: Document, target_size: int, max_size: int, overlap: int, strict: bool
) -> list[Document]:
    """Split plain text (PDF) by physical paragraphs.

    In strict mode, raises if any paragraph exceeds *max_size*.
    In non-strict mode, recursively halves oversized paragraphs instead.
    """
    raw_chunks = [c.strip() for c in doc.page_content.split("\n\n") if c.strip()]

    docs: list[Document] = []
    current_chunks: list[str] = []
    current_len = 0

    def flush() -> None:
        nonlocal current_chunks, current_len
        if not current_chunks:
            return
        docs.append(
            Document(
                page_content="\n\n".join(current_chunks),
                metadata=doc.metadata.copy(),
            )
        )
        current_chunks, current_len = _collect_overlap_blocks(current_chunks, overlap)

    def _pack(chunk: str) -> None:
        nonlocal current_len
        n = len(chunk)
        if current_len > 0 and current_len + n + 2 > target_size:
            flush()
        current_chunks.append(chunk)
        current_len += n + (2 if len(current_chunks) > 1 else 0)

    for chunk in raw_chunks:
        block_len = len(chunk)
        if strict and block_len > max_size:
            snippet = chunk[:50].replace("\n", " ") + "..."
            raise ValueError(
                f"Strict mode validation failed: A semantic block (e.g., paragraph) "
                f"exceeds the max length of {max_size} chars (actual: {block_len}). Snippet: '{snippet}'"
            )
        pieces = _halve_text(chunk, target_size) if block_len > target_size else [chunk]
        for piece in pieces:
            _pack(piece)

    flush()
    return docs


def split_text_node(state: IngestionState) -> dict:
    """Split documents into smaller chunks."""
    try:
        # Use values passed from user form (state), fallback to settings
        target_size = state.get("chunk_size", settings.ingestion.chunk_size)
        max_size = state.get("max_chunk_size", settings.ingestion.max_chunk_size)
        chunk_overlap = state.get("chunk_overlap", settings.ingestion.chunk_overlap)
        strict_mode = state.get("strict_mode", DEFAULT_STRICT_MODE)

        final_chunks = []

        for doc in state["documents"]:
            file_name = doc.metadata.get("file_name", "")
            is_md = file_name.lower().endswith(".md") or file_name.lower().endswith(
                ".markdown"
            )
            if is_md:
                final_chunks.extend(
                    _custom_split_markdown(
                        doc, target_size, max_size, chunk_overlap, strict_mode
                    )
                )
            else:
                final_chunks.extend(
                    _split_pdf(doc, target_size, max_size, chunk_overlap, strict_mode)
                )

    except Exception as exc:
        logger.error(
            "ingest_split_failed",
            {
                "doc_count": len(state["documents"]),
                "strict_mode": state.get("strict_mode", DEFAULT_STRICT_MODE),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    return {"chunks": final_chunks}


def summarize_code_node(state: IngestionState) -> dict:
    """Detect code chunks (pure or mixed), generate a summary using LLM, and update payload.

    If successful:
      - page_content = replaces ```code``` with its summary
      - metadata["chunk_type"] = "code_mixed"
      - metadata["original_content"] = original_text
    If failed or too short:
      - keeps original code in page_content
      - metadata["chunk_type"] = "text"
    """
    chunks = state.get("chunks", [])
    if not chunks:
        return {"chunks": []}
    if not settings.ingestion.enable_code_summarization:
        # Global ingestion toggle: keep chunking behavior unchanged, only skip LLM summarization.
        return {"chunks": chunks}

    llm = get_llm()
    chain = code_summarization_prompt | llm
    processed_chunks = []

    for chunk in chunks:
        text = chunk.page_content.strip()

        # Only summarize fenced code blocks that explicitly declare a language.
        code_blocks = _iter_language_fenced_blocks(text)

        has_summarized_code = False
        new_text = text

        for match in code_blocks:
            full_code_block = match.group(0)

            # Skip summarization for very short snippets
            if len(full_code_block) < 200:
                continue

            # Extract headers for context
            headers = []
            for k, v in chunk.metadata.items():
                if k.startswith("header_"):
                    headers.append(f"{k}: {v}")
            headers_str = " > ".join(headers) if headers else "无明确章节"

            language = match.group("language").strip().lower()
            code_content = match.group("content").strip()

            try:
                result = chain.invoke(
                    {"headers": headers_str, "language": language, "code": code_content}
                )

                content = getattr(result, "content", str(result))
                if isinstance(content, list):
                    content = str(content[0]) if content else ""
                summary = str(content).strip()

                # Replace the code block with its summary in the new text
                new_text = new_text.replace(full_code_block, f"\n{summary}\n")
                has_summarized_code = True

                logger.debug(
                    "code_summarized",
                    {
                        "doc_id": chunk.metadata.get("doc_id"),
                        "language": language,
                        "original_len": len(full_code_block),
                        "summary_len": len(summary),
                    },
                )

            except Exception as exc:
                # Graceful fallback: keep original content if LLM fails
                logger.warning(
                    "code_summarization_failed",
                    {
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                        "doc_id": chunk.metadata.get("doc_id"),
                        "snippet": full_code_block[:50],
                    },
                )

        if has_summarized_code:
            chunk.page_content = new_text
            chunk.metadata["chunk_type"] = "code_mixed"
            chunk.metadata["original_content"] = text
        else:
            if "chunk_type" not in chunk.metadata:
                chunk.metadata["chunk_type"] = "text"

        processed_chunks.append(chunk)

    return {"chunks": processed_chunks}


def embed_and_store_node(state: IngestionState) -> dict:
    """Embed chunks and store them in the knowledge base's Qdrant collection."""
    chunks = state["chunks"]
    kb_name = state["kb_name"]

    try:
        store = get_vector_store_for_kb(kb_name)
        store.add_documents(chunks)
    except Exception as exc:
        logger.error(
            "ingest_embed_failed",
            {
                "chunk_count": len(chunks),
                "kb_name": kb_name,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    return {"status": "success", "chunk_count": len(chunks)}
