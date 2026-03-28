"""Confluence sync service — orchestrates the full sync lifecycle.

1. Walks the remote page tree via ``ConfluenceClient``.
2. Builds a sync plan via ``build_sync_plan``.
3. Applies to create/update/delete operations using ``document_service``.
4. Records each operation in ``kb_sync_records``.
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from docmind.core import logger
from docmind.core.time import utc_now_iso
from docmind.db.repositories import (
    DocumentRepository,
    KBRepository,
    SyncJobRepository,
    SyncRecordRepository,
)
from docmind.integrations.confluence.client import ConfluenceClient, PageSummary
from docmind.integrations.confluence.converter import (
    convert_confluence_html_to_markdown,
)
from docmind.integrations.confluence.sync_planner import (
    SyncJobSummary,
    SyncPlan,
    build_sync_plan,
)
from docmind.services.document_service import (
    create_pending_document,
    delete_document_and_vectors,
    enqueue_ingestion_job,
)
from docmind.services.system_settings import (
    get_confluence_runtime_settings,
    get_runtime_settings,
)

UPLOAD_DIR = Path("data/uploads")


class SyncPreviewResult(SyncJobSummary):
    """Summary returned by a dry-run scan before a manual sync."""

    total_operations: int = 0


async def plan_sync(
    db: aiosqlite.Connection,
    kb_id: str,
) -> tuple[dict[str, Any] | None, SyncPlan | None, SyncPreviewResult | None]:
    """Build a side-effect-free sync plan for a KB."""
    kb_repo = KBRepository(db)
    doc_repo = DocumentRepository(db)

    kb = await kb_repo.get_by_id(kb_id)
    if not kb:
        return None, None, None

    root_page_id = kb.get("confluence_root_page_id", "")
    if not root_page_id:
        return kb, None, None

    confluence = get_confluence_runtime_settings()
    client = ConfluenceClient(base_url=confluence.base_url, pat=confluence.pat)

    try:
        remote_pages = await client.walk_page_tree(root_page_id)
        local_docs = await doc_repo.list_confluence_docs_by_kb(kb_id)
        plan = build_sync_plan(remote_pages, local_docs)
        summary = plan.to_summary()
        return (
            kb,
            plan,
            SyncPreviewResult(
                **summary.model_dump(),
                total_operations=plan.total_operations,
            ),
        )
    finally:
        await client.close()


def _save_markdown(doc_id: str, page_id: str, content: str) -> Path:
    """Write Markdown content to the uploads' directory."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_path = UPLOAD_DIR / f"{doc_id}_{page_id}.md"
    file_path.write_text(content, encoding="utf-8")
    return file_path


async def _apply_create(
    db: aiosqlite.Connection,
    client: ConfluenceClient,
    page: PageSummary,
    kb_id: str,
    kb_name: str,
    retrieval_mode: str,
    job_id: str,
) -> None:
    """Sync a new page: fetch body → convert → create doc → enqueue ingestion."""
    record_repo = SyncRecordRepository(db)
    doc_id = str(uuid.uuid4())

    try:
        title, html_body, version, source_url = await client.get_page_body_html(
            page.page_id
        )
        md_content = convert_confluence_html_to_markdown(html_body, source_url)

        # Full-doc size guard
        if retrieval_mode == "full_doc":
            max_chars = get_runtime_settings().retrieval.max_full_doc_chars
            if len(md_content) > max_chars:
                await record_repo.create(
                    job_id=job_id,
                    kb_id=kb_id,
                    external_doc_id=page.page_id,
                    document_title=title,
                    source_url=source_url,
                    operation="create",
                    status="failed",
                    error_message=f"Page too large for full_doc mode: {len(md_content):,} chars (limit: {max_chars:,})",
                )
                return

        file_path = _save_markdown(doc_id, page.page_id, md_content)

        await create_pending_document(
            db,
            kb_id=kb_id,
            file_name=f"{page.page_id}.md",
            title=title,
            file_path=str(file_path),
            retrieval_mode=retrieval_mode,
            user_id=None,
            doc_id=doc_id,
            source_type="confluence",
            external_doc_id=page.page_id,
            source_url=source_url,
            source_version=version,
        )

        await enqueue_ingestion_job(
            db,
            doc_id=doc_id,
            file_path=str(file_path),
            metadata={"title": title, "url": source_url},
            options={
                "retrieval_mode": retrieval_mode,
                "chunk_size": get_runtime_settings().ingestion.chunk_size,
                "chunk_overlap": get_runtime_settings().ingestion.chunk_overlap,
            },
            user_id="",
            kb_name=kb_name,
        )

        await record_repo.create(
            job_id=job_id,
            kb_id=kb_id,
            external_doc_id=page.page_id,
            document_title=title,
            source_url=source_url,
            operation="create",
            status="success",
        )
        logger.info(
            "confluence_sync_created",
            {"page_id": page.page_id, "doc_id": doc_id, "title": title},
        )

    except Exception as exc:
        await record_repo.create(
            job_id=job_id,
            kb_id=kb_id,
            external_doc_id=page.page_id,
            document_title=page.title,
            source_url=page.source_url,
            operation="create",
            status="failed",
            error_message=str(exc),
        )
        # Clean up partial file
        Path(UPLOAD_DIR / f"{doc_id}_{page.page_id}.md").unlink(missing_ok=True)
        logger.error(
            "confluence_sync_create_failed",
            {"page_id": page.page_id},
            exc=exc,
        )


async def _apply_update(
    db: aiosqlite.Connection,
    client: ConfluenceClient,
    page: PageSummary,
    old_doc: dict[str, Any],
    kb_id: str,
    kb_name: str,
    retrieval_mode: str,
    job_id: str,
) -> None:
    """Update an existing page by rebuilding its local document record."""
    record_repo = SyncRecordRepository(db)
    new_doc_id = str(uuid.uuid4())

    try:
        title, html_body, version, source_url = await client.get_page_body_html(
            page.page_id
        )
        md_content = convert_confluence_html_to_markdown(html_body, source_url)

        # Full-doc size guard — keep old doc if new content is too large
        if retrieval_mode == "full_doc":
            max_chars = get_runtime_settings().retrieval.max_full_doc_chars
            if len(md_content) > max_chars:
                await record_repo.create(
                    job_id=job_id,
                    kb_id=kb_id,
                    external_doc_id=page.page_id,
                    document_title=title,
                    source_url=source_url,
                    operation="update",
                    status="failed",
                    error_message=f"Updated page too large: {len(md_content):,} chars (limit: {max_chars:,})",
                )
                return

        file_path = _save_markdown(new_doc_id, page.page_id, md_content)

        # We intentionally delete first here to preserve the one-page-per-KB
        # uniqueness rule without introducing extra state for replacement rows.
        await delete_document_and_vectors(db, old_doc["id"])

        await create_pending_document(
            db,
            kb_id=kb_id,
            file_name=f"{page.page_id}.md",
            title=title,
            file_path=str(file_path),
            retrieval_mode=retrieval_mode,
            user_id=None,
            doc_id=new_doc_id,
            source_type="confluence",
            external_doc_id=page.page_id,
            source_url=source_url,
            source_version=version,
        )

        await enqueue_ingestion_job(
            db,
            doc_id=new_doc_id,
            file_path=str(file_path),
            metadata={"title": title, "url": source_url},
            options={
                "retrieval_mode": retrieval_mode,
                "chunk_size": get_runtime_settings().ingestion.chunk_size,
                "chunk_overlap": get_runtime_settings().ingestion.chunk_overlap,
            },
            user_id="",
            kb_name=kb_name,
        )

        await record_repo.create(
            job_id=job_id,
            kb_id=kb_id,
            external_doc_id=page.page_id,
            document_title=title,
            source_url=source_url,
            operation="update",
            status="success",
        )
        logger.info(
            "confluence_sync_updated",
            {
                "page_id": page.page_id,
                "old_doc_id": old_doc["id"],
                "new_doc_id": new_doc_id,
            },
        )

    except Exception as exc:
        await record_repo.create(
            job_id=job_id,
            kb_id=kb_id,
            external_doc_id=page.page_id,
            document_title=page.title,
            source_url=page.source_url,
            operation="update",
            status="failed",
            error_message=str(exc),
        )
        Path(UPLOAD_DIR / f"{new_doc_id}_{page.page_id}.md").unlink(missing_ok=True)
        logger.error(
            "confluence_sync_update_failed",
            {"page_id": page.page_id},
            exc=exc,
        )


async def _apply_delete(
    db: aiosqlite.Connection,
    doc: dict[str, Any],
    kb_id: str,
    job_id: str,
) -> None:
    """Delete a document whose remote Confluence page no longer exists."""
    record_repo = SyncRecordRepository(db)
    try:
        await delete_document_and_vectors(db, doc["id"])

        await record_repo.create(
            job_id=job_id,
            kb_id=kb_id,
            external_doc_id=doc["external_doc_id"],
            document_title=doc.get("title", ""),
            source_url=doc.get("source_url", ""),
            operation="delete",
            status="success",
        )
        logger.info(
            "confluence_sync_deleted",
            {"doc_id": doc["id"], "external_doc_id": doc["external_doc_id"]},
        )

    except Exception as exc:
        await record_repo.create(
            job_id=job_id,
            kb_id=kb_id,
            external_doc_id=doc["external_doc_id"],
            document_title=doc.get("title", ""),
            source_url=doc.get("source_url", ""),
            operation="delete",
            status="failed",
            error_message=str(exc),
        )
        logger.error(
            "confluence_sync_delete_failed",
            {"doc_id": doc["id"]},
            exc=exc,
        )


async def execute_sync(db: aiosqlite.Connection, kb_id: str, job_id: str) -> None:
    """Run a full Confluence sync cycle for one KB.

    Fetches remote pages, plans operations, and applies them.
    Updates the sync job and KB status fields when done.
    """
    kb_repo = KBRepository(db)
    job_repo = SyncJobRepository(db)

    kb = await kb_repo.get_by_id(kb_id)
    if not kb:
        await job_repo.update_status(job_id, "failed", "Knowledge base not found")
        return

    root_page_id = kb.get("confluence_root_page_id", "")
    if not root_page_id:
        await job_repo.update_status(
            job_id, "failed", "No Confluence root page configured"
        )
        return

    kb_name = kb["name"]
    retrieval_mode = kb.get("confluence_retrieval_mode", "chunk")
    client: ConfluenceClient | None = None

    await job_repo.update_status(job_id, "running")

    try:
        _, plan, summary = await plan_sync(db, kb_id)
        if plan is None or summary is None:
            raise ValueError("No Confluence root page configured")

        await job_repo.update_summary(job_id, summary.model_dump())

        logger.info(
            "confluence_sync_plan",
            {
                "kb_id": kb_id,
                "create": summary.created,
                "update": summary.updated,
                "delete": summary.deleted,
                "unchanged": summary.unchanged,
            },
        )

        confluence = get_confluence_runtime_settings()
        client = ConfluenceClient(base_url=confluence.base_url, pat=confluence.pat)

        for page in plan.to_create:
            await _apply_create(
                db, client, page, kb_id, kb_name, retrieval_mode, job_id
            )

        for page, old_doc in plan.to_update:
            await _apply_update(
                db, client, page, old_doc, kb_id, kb_name, retrieval_mode, job_id
            )

        for doc in plan.to_delete:
            await _apply_delete(db, doc, kb_id, job_id)

        # 5. Mark job completed
        now = utc_now_iso()
        await job_repo.update_status(job_id, "completed")
        await kb_repo.update_sync_status(
            kb_id, last_sync_at=now, last_sync_status="completed"
        )

        logger.info(
            "confluence_sync_completed",
            {"kb_id": kb_id, "job_id": job_id, "operations": plan.total_operations},
        )

    except Exception as exc:
        now = utc_now_iso()
        await job_repo.update_status(job_id, "failed", str(exc))
        await kb_repo.update_sync_status(
            kb_id, last_sync_at=now, last_sync_status="failed", last_sync_error=str(exc)
        )
        logger.error(
            "confluence_sync_failed", {"kb_id": kb_id, "job_id": job_id}, exc=exc
        )

    finally:
        if client is not None:
            await client.close()
