from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from docmind.core.exceptions import VectorStoreError
from docmind.core.metadata import META_DOC_ID, RETRIEVAL_MODE_FULL_DOC
from docmind.db.database import create_async_connection
from docmind.db.repositories import DocumentRepository, KBRepository
from docmind.services.document_service import delete_document_and_vectors
from docmind.services.system_settings import get_qdrant_runtime_settings
from docmind.vectorstore.qdrant_store import kb_collection_name

SEPARATOR = "-" * 72
QDRANT_DOC_ID_PATH = f"metadata.{META_DOC_ID}"


@dataclass(frozen=True)
class Candidate:
    document: dict
    reasons: tuple[str, ...]
    qdrant_count: int


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clean up orphaned documents whose SQLite/Qdrant/file state drifted.",
    )
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--kb-id", help="Only inspect documents under this knowledge base")
    scope.add_argument(
        "--all",
        action="store_true",
        help="Inspect documents under all knowledge bases",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete flagged documents. Omit for dry-run mode.",
    )
    return parser.parse_args()


def _qdrant_count(client, collection: str, doc_id: str) -> int:
    try:
        return client.count(
            collection_name=collection,
            count_filter=Filter(
                must=[
                    FieldCondition(
                        key=QDRANT_DOC_ID_PATH,
                        match=MatchValue(value=doc_id),
                    )
                ]
            ),
            exact=True,
        ).count
    except Exception as exc:
        raise RuntimeError(
            f"Failed to count points for doc_id={doc_id} in collection={collection}: {exc}"
        ) from exc


def _candidate_reasons(document: dict, qdrant_count: int) -> tuple[str, ...]:
    reasons: list[str] = []
    expected_count = int(document.get("chunk_count") or 0)
    retrieval_mode = str(document.get("retrieval_mode") or "")
    file_path = str(document.get("file_path") or "")

    if qdrant_count == 0:
        reasons.append("Qdrant has no chunks for this completed document")
    elif expected_count > 0 and qdrant_count != expected_count:
        reasons.append(
            f"Qdrant chunk count mismatch (db={expected_count}, qdrant={qdrant_count})"
        )

    if retrieval_mode == RETRIEVAL_MODE_FULL_DOC and file_path:
        if not Path(file_path).exists():
            reasons.append("full_doc source file is missing on disk")

    return tuple(reasons)


async def _delete_best_effort(db, document: dict) -> tuple[bool, str]:
    doc_id = str(document["id"])
    try:
        await delete_document_and_vectors(db, doc_id)
        return True, "deleted via delete_document_and_vectors"
    except Exception as exc:
        fallback_notes = [f"service delete failed: {type(exc).__name__}: {exc}"]

    file_path = str(document.get("file_path") or "")
    if file_path:
        try:
            Path(file_path).unlink(missing_ok=True)
            fallback_notes.append("local file cleanup attempted")
        except Exception as exc:
            fallback_notes.append(
                f"local file cleanup failed: {type(exc).__name__}: {exc}"
            )

    doc_repo = DocumentRepository(db)
    try:
        await doc_repo.delete(doc_id)
        fallback_notes.append("sqlite record deleted")
        return True, "; ".join(fallback_notes)
    except Exception as exc:
        fallback_notes.append(f"sqlite delete failed: {type(exc).__name__}: {exc}")
        return False, "; ".join(fallback_notes)


async def _load_target_kbs(db, kb_id: str | None) -> list[dict]:
    kb_repo = KBRepository(db)
    if kb_id is None:
        return await kb_repo.list_all()

    kb = await kb_repo.get_by_id(kb_id)
    if not kb:
        raise SystemExit(f"Knowledge base not found: {kb_id}")
    return [kb]


async def _find_candidates(db, kb_id: str | None) -> list[Candidate]:
    from qdrant_client import QdrantClient

    qdrant_url = get_qdrant_runtime_settings().url
    try:
        client = QdrantClient(url=qdrant_url, trust_env=False)
        existing_collections = {
            item.name for item in client.get_collections().collections
        }
    except Exception as exc:
        raise SystemExit(f"Unable to connect to Qdrant at {qdrant_url}: {exc}") from exc

    kb_list = await _load_target_kbs(db, kb_id)
    doc_repo = DocumentRepository(db)
    candidates: list[Candidate] = []

    for kb in kb_list:
        docs = await doc_repo.list_by_kb(kb["id"])
        collection = kb_collection_name(str(kb["name"]))
        collection_exists = collection in existing_collections

        for document in docs:
            if document.get("status") != "completed":
                continue

            doc_id = str(document["id"])
            qdrant_count = 0
            if collection_exists:
                qdrant_count = _qdrant_count(client, collection, doc_id)

            reasons = _candidate_reasons(document, qdrant_count)
            if reasons:
                candidates.append(
                    Candidate(
                        document={
                            **document,
                            "kb_name": kb["name"],
                            "kb_display_name": kb["display_name"],
                        },
                        reasons=reasons,
                        qdrant_count=qdrant_count,
                    )
                )

    return candidates


def _print_candidates(candidates: list[Candidate], apply: bool) -> None:
    mode = "APPLY" if apply else "DRY-RUN"
    print(f"{mode} | orphan document cleanup")
    print(SEPARATOR)

    if not candidates:
        print("No orphaned documents matched the cleanup rules.")
        return

    for index, candidate in enumerate(candidates, 1):
        document = candidate.document
        title = document.get("title") or document.get("file_name") or "(untitled)"
        print(
            f"{index}. doc_id={document['id']} | kb={document.get('kb_name')} | "
            f"title={title}"
        )
        print(
            f"   retrieval_mode={document.get('retrieval_mode')} | "
            f"chunk_count(db)={int(document.get('chunk_count') or 0)} | "
            f"chunk_count(qdrant)={candidate.qdrant_count}"
        )
        for reason in candidate.reasons:
            print(f"   reason: {reason}")
        file_path = str(document.get("file_path") or "")
        if file_path:
            print(f"   file_path={file_path}")
        print(SEPARATOR)


async def _apply_cleanup(db, candidates: list[Candidate]) -> None:
    deleted = 0
    failed = 0

    for candidate in candidates:
        document = candidate.document
        ok, detail = await _delete_best_effort(db, document)
        if ok:
            deleted += 1
            print(f"DELETE OK   doc_id={document['id']} | {detail}")
        else:
            failed += 1
            print(f"DELETE FAIL doc_id={document['id']} | {detail}")

    print(SEPARATOR)
    print(f"Cleanup finished: deleted={deleted}, failed={failed}")


async def _main() -> None:
    args = _parse_args()

    db = await create_async_connection()
    try:
        candidates = await _find_candidates(db, args.kb_id if not args.all else None)
        _print_candidates(candidates, apply=args.apply)
        if args.apply and candidates:
            await _apply_cleanup(db, candidates)
    finally:
        await db.close()


if __name__ == "__main__":
    try:
        asyncio.run(_main())
    except VectorStoreError as exc:
        raise SystemExit(str(exc)) from exc
