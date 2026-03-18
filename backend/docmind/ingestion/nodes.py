"""Ingestion graph nodes — each function is a LangGraph node."""

from __future__ import annotations

import re

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from docmind.core.config import settings
from docmind.core import logger
from docmind.core.llm import get_llm
from docmind.ingestion.loaders import load_document
from docmind.ingestion.state import IngestionState
from docmind.ingestion.prompts import code_summarization_prompt
from docmind.vectorstore.qdrant_store import get_vector_store_for_kb

FENCED_BLOCK_PATTERN = re.compile(r"```.*?```", flags=re.DOTALL)
# (?P<language>[a-zA-Z0-9_+-]+) and (?P<content>.*?): Named Capturing Group
# Assigns a unique label to the captured sub-pattern,
# allowing for retrieval via the variable name rather than a numeric index.
LANGUAGE_FENCED_BLOCK_PATTERN = re.compile(
    r"```(?P<language>[a-zA-Z0-9_+-]+)[ \t]*\n(?P<content>.*?)```",
    flags=re.DOTALL,
)


def load_document_node(state: IngestionState) -> dict:
    """Load documents from the given file path.

    PDF → one Document per page; Markdown → one Document for the whole file.
    User-supplied metadata (title, doc_type, department, etc.) is stamped onto
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
    retrieval_mode = state.get("retrieval_mode", "chunk")
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


def _iter_language_fenced_blocks(text: str) -> list[re.Match[str]]:
    """Return only fenced blocks that declare a language after opening backticks."""
    # finditer 是“迭代匹配”：它会在文本中不断搜索直到没有更多匹配项，
    # 相比 findall，它保留了匹配结果的完整内部状态（如起始索引、结束索引、命名捕获组数据）
    return list(LANGUAGE_FENCED_BLOCK_PATTERN.finditer(text))


def _custom_split_markdown(
    doc: Document, target_size: int, max_size: int, overlap: int
) -> list[Document]:
    """Strictly split Markdown respecting headers, code blocks, and paragraphs without Lang chain's destructive header splitter."""
    text = doc.page_content
    base_meta = doc.metadata.copy()

    # 1. Protect code blocks
    # they may contain blank lines (`\n\n`) internally. Splitting on `\n\n` directly
    # would cut them in half. By replacing each code block with a placeholder, the entire
    # block becomes a single line and won't be split. The `restore` function swaps the
    # placeholders back to the original code after all processing is done.
    text_no_code, code_blocks = _protect_fenced_blocks(text)

    # 2. Split by double newlines to get physical paragraphs
    raw_blocks = [b.strip() for b in text_no_code.split("\n\n") if b.strip()]

    docs = []
    current_chunk_texts = []
    current_len = 0
    current_headers = {}

    def build_breadcrumb(headers: dict) -> str:
        """Build a plain-text breadcrumb from the document title and current header context.

        e.g. title="API Guide", headers={"header_1": "Intro", "header_2": "Background"}
             → "API Guide / Intro / Background"
        Prepending the document title makes every chunk fully self-contained,
        which improves retrieval quality even when chunks are read in isolation.
        Plain text (no Markdown symbols) is friendlier to embedding models.
        """
        parts = []

        # Prepend document title if available
        doc_title = base_meta.get("title", "").strip()
        if doc_title:
            parts.append(doc_title)

        parts += [
            headers[f"header_{_level}"]
            for _level in sorted(int(k.split("_")[1]) for k in headers)
        ]
        return " / ".join(parts)

    def collect_overlap_blocks(blocks: list[str]) -> tuple[list[str], int]:
        """Keep as many trailing semantic blocks as fit within the overlap budget."""
        if overlap <= 0 or len(blocks) <= 1:
            return [], 0

        kept_blocks_reversed: list[str] = []
        kept_len = 0

        for _block in reversed(blocks):
            separator_len = 2 if kept_blocks_reversed else 0
            candidate_len = kept_len + separator_len + len(_block)
            if candidate_len > overlap:
                break
            kept_blocks_reversed.append(_block)
            kept_len = candidate_len

        kept_blocks = list(reversed(kept_blocks_reversed))
        return kept_blocks, kept_len

    def flush_chunk():
        nonlocal current_chunk_texts, current_len
        if not current_chunk_texts:
            return

        body = "\n\n".join(current_chunk_texts)

        # Prepend the header breadcrumb so every chunk is self-contained and
        # embedding-friendly. The breadcrumb length is NOT counted toward
        # current_len to keep the splitting logic unaffected.
        breadcrumb = build_breadcrumb(current_headers)
        merged_text = f"{breadcrumb}\n\n{body}" if breadcrumb else body

        meta = base_meta.copy()
        meta.update(current_headers)
        docs.append(Document(page_content=merged_text, metadata=meta))

        current_chunk_texts, current_len = collect_overlap_blocks(current_chunk_texts)

    header_pattern = re.compile(r"^(#{1,6})\s+(.*)")

    for block in raw_blocks:
        # Check if this block is a header
        h_match = header_pattern.match(block)
        if h_match:
            level = len(h_match.group(1))
            header_text = h_match.group(2).strip()

            # Flush current chunk before changing headers context to prevent semantic leakage
            flush_chunk()

            # Remove any existing headers that are at the same or deeper level
            keys_to_remove = [
                k for k in current_headers.keys() if int(k.split("_")[1]) >= level
            ]
            for k in keys_to_remove:
                del current_headers[k]

            current_headers[f"header_{level}"] = header_text
            continue

        restored_block = _restore_fenced_block_placeholders(block, code_blocks)
        block_len = len(restored_block)

        # Strict validation against MAX_SIZE
        if block_len > max_size:
            snippet = restored_block[:50].replace("\n", " ") + "..."
            raise ValueError(
                f"Strict mode validation failed: A semantic block (e.g., paragraph or code block) "
                f"exceeds the max length of {max_size} chars (actual: {block_len}). Snippet: '{snippet}'"
            )

        # If adding this block exceeds target_size, flush the current basket first
        if current_len > 0 and current_len + block_len + 2 > target_size:
            flush_chunk()

        # Add the block to the current basket
        current_chunk_texts.append(restored_block)
        current_len += block_len + (2 if len(current_chunk_texts) > 1 else 0)

    # Flush any remaining text
    flush_chunk()
    return docs


def _strict_split_pdf(
    doc: Document, target_size: int, max_size: int, overlap: int
) -> list[Document]:
    """Strictly split plain text (PDF) by physical paragraphs."""
    raw_chunks = [c.strip() for c in doc.page_content.split("\n\n") if c.strip()]

    docs = []
    current_chunks = []
    current_len = 0

    for chunk in raw_chunks:
        block_len = len(chunk)
        if block_len > max_size:
            snippet = chunk[:50].replace("\n", " ") + "..."
            raise ValueError(
                f"Strict mode validation failed: A semantic block (e.g., paragraph) "
                f"exceeds the max length of {max_size} chars (actual: {block_len}). Snippet: '{snippet}'"
            )

        if current_len > 0 and current_len + block_len + 2 > target_size:
            docs.append(
                Document(
                    page_content="\n\n".join(current_chunks),
                    metadata=doc.metadata.copy(),
                )
            )

            # overlap logic
            if overlap > 0 and len(current_chunks) > 1:
                last_block = current_chunks[-1]
                if len(last_block) <= overlap:
                    current_chunks = [last_block]
                    current_len = len(last_block)
                else:
                    current_chunks = []
                    current_len = 0
            else:
                current_chunks = []
                current_len = 0

        current_chunks.append(chunk)
        current_len += block_len + (2 if len(current_chunks) > 1 else 0)

    if current_chunks:
        docs.append(
            Document(
                page_content="\n\n".join(current_chunks), metadata=doc.metadata.copy()
            )
        )

    return docs


def split_text_node(state: IngestionState) -> dict:
    """Split documents into smaller chunks."""
    try:
        # Use values passed from user form (state), fallback to settings
        target_size = state.get("chunk_size", settings.ingestion.chunk_size)
        max_size = state.get("max_chunk_size", 1500)
        chunk_overlap = settings.ingestion.chunk_overlap
        strict_mode = state.get("strict_mode", True)

        final_chunks = []

        for doc in state["documents"]:
            if strict_mode:
                file_name = doc.metadata.get("file_name", "")
                is_md = file_name.lower().endswith(".md") or file_name.lower().endswith(
                    ".markdown"
                )

                if is_md:
                    final_chunks.extend(
                        _custom_split_markdown(
                            doc, target_size, max_size, chunk_overlap
                        )
                    )
                else:
                    final_chunks.extend(
                        _strict_split_pdf(doc, target_size, max_size, chunk_overlap)
                    )
            else:
                # Fallback to violent recursive character splitting using target_size
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=target_size,
                    chunk_overlap=chunk_overlap,
                )
                final_chunks.extend(splitter.split_documents([doc]))

        chunks: list[Document] = final_chunks
    except Exception as exc:
        logger.error(
            "ingest_split_failed",
            {
                "doc_count": len(state["documents"]),
                "strict_mode": state.get("strict_mode", True),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    return {"chunks": chunks}


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
