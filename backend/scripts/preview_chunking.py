"""Preview the real chunking output for a Markdown or PDF document.

Run from the backend directory:
    uv run python scripts/preview_chunking.py scripts/samples/chunking_preview_demo.md

Example:
    uv run python scripts/preview_chunking.py scripts/samples/chunking_preview_demo.md \
        --chunk-size 260 \
        --max-chunk-size 420 \
        --chunk-overlap 120 \
        --strict-mode false \
        --show-documents
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.documents import Document

from docmind.ingestion.nodes import load_document_node, split_text_node

SECTION_LINE = "=" * 88
SUBSECTION_LINE = "-" * 88


def _parse_bool(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(
        f"Invalid boolean value '{value}'. Use true/false."
    )


def _format_metadata(doc: Document) -> str:
    return json.dumps(doc.metadata, ensure_ascii=False, indent=2, sort_keys=True)


def _print_documents(documents: list[Document]) -> None:
    print(SECTION_LINE)
    print(f"Loaded documents: {len(documents)}")
    print(SECTION_LINE)

    for index, doc in enumerate(documents, start=1):
        print(f"[Document {index}/{len(documents)}] length={len(doc.page_content)}")
        print("metadata:")
        print(_format_metadata(doc))
        print("content:")
        print(doc.page_content.strip())
        print()


def _print_chunks(chunks: list[Document]) -> None:
    print(SECTION_LINE)
    print(f"Generated chunks: {len(chunks)}")
    print(SECTION_LINE)

    for index, chunk in enumerate(chunks, start=1):
        print(
            f"[Chunk {index}/{len(chunks)}] length={len(chunk.page_content)} "
            f"chunk_type={chunk.metadata.get('chunk_type', 'text')}"
        )
        print("metadata:")
        print(_format_metadata(chunk))
        print("content:")
        print(chunk.page_content.strip())
        print(SUBSECTION_LINE)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview the real DocMind chunking output for a Markdown or PDF file."
    )
    parser.add_argument("file", type=str, help="Path to the file (.md or .pdf)")
    parser.add_argument(
        "--title",
        type=str,
        default="",
        help="Optional title used in chunk breadcrumbs. Defaults to the file stem.",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=500,
        help="Target chunk size passed into split_text_node.",
    )
    parser.add_argument(
        "--max-chunk-size",
        type=int,
        default=1000,
        help="Max semantic block size used by strict mode.",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=120,
        help="Overlap budget passed into split_text_node.",
    )
    parser.add_argument(
        "--strict-mode",
        type=_parse_bool,
        default=True,
        help="Whether to raise on oversized semantic blocks. Use true/false.",
    )
    parser.add_argument(
        "--retrieval-mode",
        type=str,
        default="chunk",
        help="Metadata field to stamp into the loaded documents.",
    )
    parser.add_argument(
        "--show-documents",
        action="store_true",
        help="Print the raw loaded documents before chunking.",
    )

    args = parser.parse_args()

    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        sys.exit(1)

    state = {
        "file_path": str(file_path),
        "metadata": {"title": args.title or file_path.stem},
        "doc_id": "preview-doc",
        "user_id": "preview-user",
        "kb_name": "preview-kb",
        "retrieval_mode": args.retrieval_mode,
        "chunk_size": args.chunk_size,
        "max_chunk_size": args.max_chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "strict_mode": args.strict_mode,
    }

    print(SECTION_LINE)
    print("Chunking preview configuration")
    print(SECTION_LINE)
    print(f"file:            {file_path}")
    print(f"title:           {args.title or file_path.stem}")
    print(f"chunk_size:      {args.chunk_size}")
    print(f"max_chunk_size:  {args.max_chunk_size}")
    print(f"chunk_overlap:   {args.chunk_overlap}")
    print(f"strict_mode:     {args.strict_mode}")
    print(f"retrieval_mode:  {args.retrieval_mode}")
    print()

    try:
        loaded = load_document_node(state)
        documents = loaded["documents"]
        if args.show_documents:
            _print_documents(documents)

        result = split_text_node({**state, **loaded})
        chunks = result["chunks"]
        _print_chunks(chunks)
    except Exception as exc:
        print(
            f"Error: preview failed - {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
