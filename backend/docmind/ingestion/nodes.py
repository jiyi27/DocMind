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
    for doc in docs:
        doc.metadata.update(metadata)
        doc.metadata["doc_id"] = doc_id
        doc.metadata["user_id"] = user_id
        doc.metadata["kb_name"] = kb_name

    return {"documents": docs}


def _custom_split_markdown(
    doc: Document, target_size: int, max_size: int, overlap: int
) -> list[Document]:
    """Strictly split Markdown respecting headers, code blocks, and paragraphs without Langchain's destructive header splitter."""
    text = doc.page_content
    base_meta = doc.metadata.copy()

    # 1. Protect code blocks
    code_blocks = []

    def replacer(match):
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    text_no_code = re.sub(r"```.*?```", replacer, text, flags=re.DOTALL)

    # 2. Split by double newlines to get physical paragraphs
    raw_blocks = [b.strip() for b in text_no_code.split("\n\n") if b.strip()]

    docs = []
    current_chunk_texts = []
    current_len = 0
    current_headers = {}

    def flush_chunk():
        nonlocal current_chunk_texts, current_len
        if not current_chunk_texts:
            return

        merged_text = "\n\n".join(current_chunk_texts)
        meta = base_meta.copy()
        meta.update(current_headers)
        docs.append(Document(page_content=merged_text, metadata=meta))

        # Overlap handling: take the last block if it fits within overlap limit
        if overlap > 0 and len(current_chunk_texts) > 1:
            last_block = current_chunk_texts[-1]
            if len(last_block) <= overlap:
                current_chunk_texts = [last_block]
                current_len = len(last_block)
            else:
                current_chunk_texts = []
                current_len = 0
        else:
            current_chunk_texts = []
            current_len = 0

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

        # Restore code blocks in this specific paragraph
        def restore(m):
            idx = int(m.group(1))
            return code_blocks[idx]

        restored_block = re.sub(r"__CODE_BLOCK_(\d+)__", restore, block)
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

        # Find all markdown code blocks in the chunk
        code_blocks = list(re.finditer(r"```(.*?)```", text, flags=re.DOTALL))

        has_summarized_code = False
        new_text = text

        for match in code_blocks:
            full_code_block = match.group(0)

            # Skip summarization for very short snippets
            if len(full_code_block) < 100:
                continue

            # Extract headers for context
            headers = []
            for k, v in chunk.metadata.items():
                if k.startswith("header_"):
                    headers.append(f"{k}: {v}")
            headers_str = " > ".join(headers) if headers else "无明确章节"

            # Try to extract language from the first line
            first_line = full_code_block.split("\n", 1)[0]
            language = first_line.strip("`").strip() or "unknown"

            code_content = full_code_block.strip("```").strip()
            if code_content.startswith(language):
                code_content = code_content[len(language) :].strip()

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
