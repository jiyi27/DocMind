"""Synchronous SQLite repository for ingestion queue state transitions."""

from __future__ import annotations

import sqlite3
from typing import Any

from docmind.core.time import utc_now_iso


class IngestionQueueRepository:
    """Owns queue-specific state transitions used by the background worker."""

    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def requeue_processing_jobs(self) -> None:
        """Recovery routine executed ONCE at worker startup.

        When the worker restarts (e.g., after a crash), any jobs left in
        'processing' state are considered orphaned. This method resets them
        to 'pending' so they can be re-claimed and re-processed.

        Note: This runs only once at the beginning of `_run()`, before the
        main polling loop starts.
        """
        now = utc_now_iso()
        # Step 1: Reset orphaned ingestion jobs to 'pending' for reprocessing
        self.db.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'pending',
                error_message = '',
                claimed_at = '',
                started_at = '',
                finished_at = '',
                updated_at = ?
            WHERE status = 'processing'
            """,
            (now,),
        )
        # Step 2: Sync the linked documents' status to match the reset jobs
        self.db.execute(
            """
            UPDATE documents
            SET status = 'pending',
                error_message = ''
            WHERE id IN (
                SELECT document_id
                FROM ingestion_jobs
                WHERE status = 'pending'
            )
            """
        )
        self.db.commit()

    def claim_next_pending_job(self) -> dict[str, Any] | None:
        row = self.db.execute(
            """
            SELECT *
            FROM ingestion_jobs
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            return None

        now = utc_now_iso()
        result = self.db.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'processing',
                attempt_count = attempt_count + 1,
                error_message = '',
                claimed_at = ?,
                started_at = ?,
                updated_at = ?
            WHERE id = ? AND status = 'pending'
            """,
            (now, now, now, row["id"]),
        )
        if result.rowcount == 0:
            self.db.rollback()
            return None

        self.db.execute(
            """
            UPDATE documents
            SET status = 'processing',
                error_message = ''
            WHERE id = ?
            """,
            (row["document_id"],),
        )
        self.db.commit()

        claimed = dict(row)
        claimed["status"] = "processing"
        claimed["attempt_count"] = row["attempt_count"] + 1
        claimed["error_message"] = ""
        claimed["claimed_at"] = now
        claimed["started_at"] = now
        claimed["updated_at"] = now
        return claimed

    def mark_completed(self, job_id: str, document_id: str, chunk_count: int) -> None:
        now = utc_now_iso()
        self.db.execute(
            """
            UPDATE documents
            SET status = 'completed',
                error_message = '',
                chunk_count = ?
            WHERE id = ?
            """,
            (chunk_count, document_id),
        )
        self.db.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'completed',
                error_message = '',
                finished_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, job_id),
        )
        self.db.commit()

    def mark_failed(self, job_id: str, document_id: str, error_message: str) -> None:
        now = utc_now_iso()
        self.db.execute(
            """
            UPDATE documents
            SET status = 'failed',
                error_message = ?
            WHERE id = ?
            """,
            (error_message, document_id),
        )
        self.db.execute(
            """
            UPDATE ingestion_jobs
            SET status = 'failed',
                error_message = ?,
                finished_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (error_message, now, now, job_id),
        )
        self.db.commit()
