"""Debug script — inspect what retrieve() actually sends to the LLM.

Usage:
    uv run python scripts/debug_retrieval.py --kb <kb_name> --query "your question"
    uv run python scripts/debug_retrieval.py --kb <kb_name> --doc-id <doc_id>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEPARATOR = "─" * 72


def cmd_retrieve(kb_name: str, query: str) -> None:
    from docmind.core.config import settings
    from docmind.retrieval.nodes import retrieve
    from docmind.vectorstore.qdrant_store import get_vector_store_for_kb

    # 1. Raw Qdrant hits — what came back before selection logic
    store = get_vector_store_for_kb(kb_name)
    raw_results = store.similarity_search_with_score(query, k=settings.retrieval.top_k)

    print(f"\nQuery : {query!r}")
    print(f"KB    : {kb_name}  |  top_k={settings.retrieval.top_k}  "
          f"max_full_docs={settings.retrieval.max_full_docs}  "
          f"max_full_doc_chars={settings.retrieval.max_full_doc_chars:,}")
    print(f"\nRaw Qdrant hits ({len(raw_results)}):")
    print(SEPARATOR)
    for rank, (doc, score) in enumerate(raw_results, 1):
        meta = doc.metadata or {}
        mode = meta.get("retrieval_mode", "chunk")
        doc_id = meta.get("doc_id", "?")
        title = meta.get("title") or meta.get("file_name", "?")
        print(f"  [{rank}] score={score:.4f}  mode={mode}  doc_id={doc_id[:8]}…  {title!r}")

    # 2. Call the real production retrieve() — identical to what the API does
    context, sources = retrieve(query, kb_name)

    print(f"\n{SEPARATOR}")
    print("Context sent to LLM (via production retrieve()):")
    print(SEPARATOR)

    if not context:
        print("  (empty — no results matched)")
    else:
        # Split back into numbered blocks for readability
        import re
        blocks = re.split(r'(?=\[\d+\] )', context)
        for block in blocks:
            block = block.strip()
            if not block:
                continue
            preview = block[:400].replace("\n", " ")
            print(f"\n  {preview}{'…' if len(block) > 400 else ''}")
            print(f"  ({len(block):,} chars)")

    print(f"\n{SEPARATOR}")
    print(f"Total context: {len(context):,} chars")
    print(f"Sources: {sources}")


def cmd_chunks(kb_name: str, doc_id: str) -> None:
    from docmind.vectorstore.qdrant_store import get_chunks_by_doc_id

    result = get_chunks_by_doc_id(kb_name, doc_id, offset=0, limit=100)
    total = result["total"]

    print(f"\nDoc ID : {doc_id}")
    print(f"KB     : {kb_name}")
    print(f"Chunks in Qdrant: {total}")

    if total == 0:
        print("(No chunks found — document was deleted or never ingested)")
        return

    print(f"\n{SEPARATOR}")
    for item in result["items"]:
        mode = item["metadata"].get("retrieval_mode", "chunk")
        preview = item["content"][:120].replace("\n", " ")
        print(f"  point_id={item['point_id'][:8]}…  mode={mode}  {item['char_count']:,} chars")
        print(f"  {preview}…\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Debug DocMind retrieval")
    parser.add_argument("--kb", required=True, help="Knowledge base slug")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--query", help="Query string — shows full retrieval context")
    group.add_argument("--doc-id", help="Document ID — shows chunks in Qdrant")
    args = parser.parse_args()

    if args.query:
        cmd_retrieve(args.kb, args.query)
    else:
        cmd_chunks(args.kb, args.doc_id)


if __name__ == "__main__":
    main()
