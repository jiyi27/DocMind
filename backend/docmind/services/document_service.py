"""Reusable document lifecycle operations.

Extracted from the ingest router so that both manual uploads and
Confluence sync can share the same create / enqueue / delete logic.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from docmind.db.repositories import (
    DocumentRepository,
    IngestionJobRepository,
    KBRepository,
)
from docmind.vectorstore.qdrant_store import delete_documents_by_doc_id


async def create_pending_document(
    db: aiosqlite.Connection,
    *,
    kb_id: str,
    file_name: str,
    title: str,
    file_path: str,
    retrieval_mode: str = "chunk",
    user_id: str | None = None,
    doc_id: str | None = None,
    source_type: str = "manual",
    external_doc_id: str = "",
    source_url: str = "",
    source_version: int = 0,
) -> dict[str, Any]:
    """Insert a pending document row in SQLite and return its dict."""
    _id = doc_id or str(uuid.uuid4())
    doc_repo = DocumentRepository(db)
    return await doc_repo.create(
        user_id=user_id,
        kb_id=kb_id,
        file_name=file_name,
        title=title,
        doc_id=_id,
        status="pending",
        file_path=file_path,
        retrieval_mode=retrieval_mode,
        source_type=source_type,
        external_doc_id=external_doc_id,
        source_url=source_url,
        source_version=source_version,
    )


async def enqueue_ingestion_job(
    db: aiosqlite.Connection,
    *,
    doc_id: str,
    file_path: str,
    metadata: dict[str, Any],
    options: dict[str, Any],
    user_id: str,
    kb_name: str,
) -> dict[str, Any]:
    """Create an ingestion_jobs record so the worker picks it up."""
    job_repo = IngestionJobRepository(db)
    payload = {
        "file_path": file_path,
        "metadata": metadata,
        "options": options,
        "user_id": user_id,
        "doc_id": doc_id,
        "kb_name": kb_name,
    }
    return await job_repo.create_pending(
        document_id=doc_id,
        payload_json=json.dumps(payload, ensure_ascii=False),
    )


async def delete_document_and_vectors(
    db: aiosqlite.Connection,
    doc_id: str,
) -> None:
    """Delete a document and its Qdrant vectors using the doc's real kb_id."""
    doc_repo = DocumentRepository(db)
    kb_repo = KBRepository(db)

    doc = await doc_repo.get_by_id(doc_id)
    if not doc:
        return

    kb = await kb_repo.get_by_id(doc["kb_id"])
    if kb:
        delete_documents_by_doc_id(kb["name"], doc_id)

    # Delete the local file if it exists
    file_path = doc.get("file_path", "")
    if file_path:
        Path(file_path).unlink(missing_ok=True)

    await doc_repo.delete(doc_id)
