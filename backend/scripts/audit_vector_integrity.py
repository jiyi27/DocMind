# -----------------------------------------------------------------------------
# audit_vector_integrity.py
#
# Diagnostic tool for verifying consistency between the Qdrant vector store
# and SQLite document records. Useful for detecting data drift after document
# deletions, failed ingestion jobs, or storage migrations.
#
# Two modes:
#   --doc-id      Check a specific document: compare SQLite chunk_count against
#                 the actual number of points in Qdrant. Also reports orphan
#                 vectors if the document no longer exists in SQLite.
#
#   --scan-orphans  Scroll through every Qdrant collection and flag any
#                   doc_id that has no corresponding SQLite record.
#
# Usage (run from the /backend directory):
#   uv run python scripts/audit_vector_integrity.py --doc-id <doc_id>
#   uv run python scripts/audit_vector_integrity.py --scan-orphans
# -----------------------------------------------------------------------------

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from docmind.core.config import settings
from docmind.db.database import create_async_connection
from docmind.db.repositories import DocumentRepository
from docmind.vectorstore.qdrant_store import _QDRANT_DOC_ID_PATH, kb_collection_name

SEPARATOR = "─" * 64


def _qdrant_count(client: QdrantClient, collection: str, doc_id: str) -> int:
    try:
        return client.count(
            collection_name=collection,
            count_filter=Filter(
                must=[FieldCondition(key=_QDRANT_DOC_ID_PATH, match=MatchValue(value=doc_id))]
            ),
            exact=True,
        ).count
    except Exception:
        return -1  # collection may not exist


async def check_single(doc_id: str) -> None:
    client = QdrantClient(url=settings.qdrant.url)
    collections = [c.name for c in client.get_collections().collections]

    db = await create_async_connection()
    try:
        doc_repo = DocumentRepository(db)
        doc = await doc_repo.get_by_id_with_display_info(doc_id)
    finally:
        await db.close()

    if not doc:
        print(f"[NOT IN SQLite] doc_id={doc_id}")
        # Still check Qdrant to detect orphan vectors
        orphan_total = 0
        for col in collections:
            n = _qdrant_count(client, col, doc_id)
            if n > 0:
                print(f"  WARNING  orphan: {n} point(s) in collection '{col}'")
                orphan_total += n
        if orphan_total == 0:
            print("  OK  No orphan vectors found in any collection.")
        return

    kb_name = doc.get("kb_name")
    print(f"\nDocument : {doc_id}")
    print(f"Title    : {doc.get('title') or doc.get('file_name')}")
    print(f"Status   : {doc.get('status')}")
    print(f"KB name  : {kb_name or '(KB record missing!)'}")

    if not kb_name:
        print("WARNING  KB record is gone — cannot look up Qdrant collection.")
        print("         If KB was deleted via API, its entire collection was dropped.")
        return

    col = kb_collection_name(kb_name)
    count = _qdrant_count(client, col, doc_id)

    print(f"Collection       : {col}")
    print(f"chunk_count (DB) : {doc.get('chunk_count', 'n/a')}")
    print(f"Points in Qdrant : {count}")
    print(SEPARATOR)

    db_count = doc.get("chunk_count") or 0
    if count == db_count and count > 0:
        print("OK  Qdrant and SQLite are consistent.")
    elif count == 0:
        print("OK  Qdrant is clean — document was deleted or never ingested.")
    else:
        print(f"WARNING  Mismatch: Qdrant has {count} point(s), SQLite chunk_count={db_count}")


async def scan_orphans() -> None:
    """Scroll all Qdrant points and check each doc_id against SQLite."""
    client = QdrantClient(url=settings.qdrant.url)
    collections = [c.name for c in client.get_collections().collections]

    db = await create_async_connection()
    try:
        doc_repo = DocumentRepository(db)
        orphan_total = 0

        for col in collections:
            # Collect doc_id → point count from Qdrant
            seen: dict[str, int] = {}
            offset = None
            while True:
                points, next_offset = client.scroll(
                    collection_name=col,
                    offset=offset,
                    limit=250,
                    with_payload=True,
                    with_vectors=False,
                )
                for p in points:
                    doc_id = (p.payload or {}).get("metadata", {}).get("doc_id")
                    if doc_id:
                        seen[doc_id] = seen.get(doc_id, 0) + 1
                if next_offset is None:
                    break
                offset = next_offset

            print(f"\nCollection '{col}': {len(seen)} unique doc_id(s), checking SQLite…")

            for doc_id, point_count in seen.items():
                doc = await doc_repo.get_by_id(doc_id)
                if not doc:
                    print(
                        f"  WARNING  orphan | doc_id={doc_id} | "
                        f"{point_count} point(s) in Qdrant but no SQLite record"
                    )
                    orphan_total += point_count

    finally:
        await db.close()

    print(f"\n{SEPARATOR}")
    if orphan_total == 0:
        print("OK  No orphan vectors found across all collections.")
    else:
        print(f"WARNING  Total orphan points: {orphan_total}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Qdrant vector integrity.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--doc-id", help="Check a specific document by ID")
    group.add_argument(
        "--scan-orphans",
        action="store_true",
        help="Scan all collections for chunks with no matching SQLite record",
    )
    args = parser.parse_args()

    if args.doc_id:
        asyncio.run(check_single(args.doc_id))
    else:
        asyncio.run(scan_orphans())


if __name__ == "__main__":
    main()
