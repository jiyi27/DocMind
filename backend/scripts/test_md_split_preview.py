"""
Preview how _custom_split_markdown handles different Markdown structures.

Compares three strategies side by side:
  - current:    existing implementation (no special handling)
  - blockquote: protect blockquotes as atomic units + strip '>' prefix
  - table:      protect tables as atomic units + convert pipe syntax to key:value lines

Run from the backend directory:
    python scripts/test_md_split_preview.py
"""

from __future__ import annotations

import re
import sys
import textwrap
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.documents import Document

from docmind.ingestion.nodes import _custom_split_markdown

# ── constants ────────────────────────────────────────────────────────────────

SAMPLE_MD = Path(__file__).with_name("test_md_split_preview.md").read_text()

TARGET_SIZE = 400
MAX_SIZE = 1200
OVERLAP = 80

SEPARATOR = "─" * 72

# ── blockquote helpers ────────────────────────────────────────────────────────

_BLOCKQUOTE_PATTERN = re.compile(
    r"(?:^[ \t]*>[ \t]?.*\n?)+",
    flags=re.MULTILINE,
)


def _protect_blockquotes(text: str) -> tuple[str, list[str]]:
    """Replace contiguous blockquote regions with placeholders."""
    blocks: list[str] = []

    def replacer(m: re.Match[str]) -> str:
        # Strip '>' prefix from each line for cleaner text
        clean_lines = []
        for line in m.group(0).splitlines():
            stripped = re.sub(r"^[ \t]*>[ \t]?", "", line)
            clean_lines.append(stripped)
        clean_text = "\n".join(clean_lines).strip()
        blocks.append(clean_text)
        return f"\n\n__BLOCKQUOTE_{len(blocks) - 1}__\n\n"

    return _BLOCKQUOTE_PATTERN.sub(replacer, text), blocks


def _restore_blockquotes(text: str, blocks: list[str]) -> str:
    return re.sub(
        r"__BLOCKQUOTE_(\d+)__",
        lambda m: f"[引用]\n{blocks[int(m.group(1))]}",
        text,
    )


# ── table helpers ─────────────────────────────────────────────────────────────

_TABLE_PATTERN = re.compile(
    r"(?:^[ \t]*\|.+\|[ \t]*\n)+",
    flags=re.MULTILINE,
)


def _parse_table_to_text(raw_table: str) -> str:
    """Convert a Markdown pipe table to readable key:value lines."""
    lines = [l.strip() for l in raw_table.strip().splitlines() if l.strip()]

    # Find separator row (e.g. |---|---|)
    sep_idx = next(
        (i for i, l in enumerate(lines) if re.match(r"^\|[-| :]+\|$", l)),
        None,
    )
    if sep_idx is None or sep_idx == 0:
        return raw_table  # not a standard table, keep as-is

    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    data_lines = lines[sep_idx + 1 :]

    rows = []
    for line in data_lines:
        cells = [c.strip() for c in line.strip("|").split("|")]
        pairs = ", ".join(
            f"{h}: {c}"
            for h, c in zip(headers, cells)
            if c  # skip empty cells
        )
        if pairs:
            rows.append(pairs)

    return "[表格]\n" + "\n".join(rows)


def _protect_tables(text: str) -> tuple[str, list[str]]:
    blocks: list[str] = []

    def replacer(m: re.Match[str]) -> str:
        blocks.append(_parse_table_to_text(m.group(0)))
        return f"\n\n__TABLE_{len(blocks) - 1}__\n\n"

    return _TABLE_PATTERN.sub(replacer, text), blocks


def _restore_tables(text: str, blocks: list[str]) -> str:
    return re.sub(
        r"__TABLE_(\d+)__",
        lambda m: blocks[int(m.group(1))],
        text,
    )


# ── patched splitter variants ─────────────────────────────────────────────────

def split_with_blockquote_protection(
    doc: Document, target_size: int, max_size: int, overlap: int
) -> list[Document]:
    """Wrap _custom_split_markdown: protect blockquotes before splitting."""
    original_content = doc.page_content
    protected, bq_blocks = _protect_blockquotes(original_content)

    patched_doc = Document(page_content=protected, metadata=doc.metadata.copy())
    chunks = _custom_split_markdown(patched_doc, target_size, max_size, overlap)

    # Restore blockquote content in each chunk
    for chunk in chunks:
        chunk.page_content = _restore_blockquotes(chunk.page_content, bq_blocks)
    return chunks


def split_with_table_conversion(
    doc: Document, target_size: int, max_size: int, overlap: int
) -> list[Document]:
    """Wrap _custom_split_markdown: convert tables to prose before splitting."""
    original_content = doc.page_content
    protected, table_blocks = _protect_tables(original_content)

    patched_doc = Document(page_content=protected, metadata=doc.metadata.copy())
    chunks = _custom_split_markdown(patched_doc, target_size, max_size, overlap)

    for chunk in chunks:
        chunk.page_content = _restore_tables(chunk.page_content, table_blocks)
    return chunks


def split_with_both(
    doc: Document, target_size: int, max_size: int, overlap: int
) -> list[Document]:
    """Protect blockquotes AND convert tables, then split."""
    text = doc.page_content
    text, bq_blocks = _protect_blockquotes(text)
    text, table_blocks = _protect_tables(text)

    patched_doc = Document(page_content=text, metadata=doc.metadata.copy())
    chunks = _custom_split_markdown(patched_doc, target_size, max_size, overlap)

    for chunk in chunks:
        chunk.page_content = _restore_blockquotes(chunk.page_content, bq_blocks)
        chunk.page_content = _restore_tables(chunk.page_content, table_blocks)
    return chunks


# ── display ───────────────────────────────────────────────────────────────────

def print_chunks(label: str, chunks: list[Document]) -> None:
    print(f"\n{'═' * 72}")
    print(f"  策略: {label}  （共 {len(chunks)} 个 chunk）")
    print(f"{'═' * 72}")
    for i, chunk in enumerate(chunks, 1):
        headers = {k: v for k, v in chunk.metadata.items() if k.startswith("header_")}
        header_info = "  ".join(f"{k}={v}" for k, v in sorted(headers.items())) or "（无 header 上下文）"
        content_len = len(chunk.page_content)
        print(f"\n  [{i}/{len(chunks)}] 长度={content_len}  {header_info}")
        print(SEPARATOR)
        # Indent content for readability
        indented = textwrap.indent(chunk.page_content, "  │ ")
        print(indented)
    print()


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    base_doc = Document(
        page_content=SAMPLE_MD,
        metadata={"file_name": "test_md_split_preview.md", "title": "API 接口文档"},
    )

    print(f"\n目标分块大小: {TARGET_SIZE}  最大: {MAX_SIZE}  重叠: {OVERLAP}\n")

    strategies = [
        ("当前实现（无特殊处理）", _custom_split_markdown),
        ("仅保护 Blockquote", split_with_blockquote_protection),
        ("仅转换 Table", split_with_table_conversion),
        ("Blockquote + Table 全部处理", split_with_both),
    ]

    for label, fn in strategies:
        try:
            chunks = fn(base_doc, TARGET_SIZE, MAX_SIZE, OVERLAP)
            print_chunks(label, chunks)
        except Exception as exc:
            print(f"\n[ERROR] {label}: {exc}\n")


if __name__ == "__main__":
    main()
