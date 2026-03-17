"""Persistent ingestion queue worker backed by SQLite."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any

from docmind.core import logger
from docmind.core.time import utc_now_iso
from docmind.db.database import get_db_path
from docmind.ingestion.graph import ingestion_graph

POLL_INTERVAL_SECONDS = 1.0


class IngestionQueueWorker:
    """Single-threaded worker that consumes pending ingestion jobs."""

    def __init__(self, poll_interval: float = POLL_INTERVAL_SECONDS) -> None:
        self.poll_interval = poll_interval
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="docmind-ingestion-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info("ingestion_worker_started", {"poll_interval": self.poll_interval})

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        logger.info("ingestion_worker_stopped", {})

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _run(self) -> None:
        conn = self._connect()
        try:
            self._requeue_processing_jobs(conn)
            while not self._stop_event.is_set():
                job = self._claim_next_job(conn)
                if job is None:
                    self._stop_event.wait(self.poll_interval)
                    continue

                self._process_job(conn, job)
        finally:
            conn.close()

    def _requeue_processing_jobs(self, conn: sqlite3.Connection) -> None:
        now = utc_now_iso()
        conn.execute(
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
        conn.execute(
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
        conn.commit()

    def _claim_next_job(self, conn: sqlite3.Connection) -> dict[str, Any] | None:
        row = conn.execute(
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
        result = conn.execute(
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
            conn.rollback()
            return None

        conn.execute(
            """
            UPDATE documents
            SET status = 'processing',
                error_message = ''
            WHERE id = ?
            """,
            (row["document_id"],),
        )
        conn.commit()

        claimed = dict(row)
        claimed["status"] = "processing"
        claimed["attempt_count"] = row["attempt_count"] + 1
        claimed["error_message"] = ""
        claimed["claimed_at"] = now
        claimed["started_at"] = now
        claimed["updated_at"] = now
        return claimed

    def _process_job(self, conn: sqlite3.Connection, job: dict[str, Any]) -> None:
        payload = json.loads(job["payload_json"])
        document_id = job["document_id"]
        file_path = payload["file_path"]

        try:
            result = ingestion_graph.invoke(payload)
            chunk_count = result.get("chunk_count", 0)
            self._mark_completed(conn, job["id"], document_id, chunk_count)
            logger.info(
                "ingestion_job_completed",
                {
                    "job_id": job["id"],
                    "document_id": document_id,
                    "chunk_count": chunk_count,
                },
            )
        except Exception as exc:
            self._mark_failed(conn, job["id"], document_id, str(exc))
            logger.error(
                "ingestion_job_failed",
                {"job_id": job["id"], "document_id": document_id},
                exc=exc,
            )
        finally:
            Path(file_path).unlink(missing_ok=True)

    def _mark_completed(
        self,
        conn: sqlite3.Connection,
        job_id: str,
        document_id: str,
        chunk_count: int,
    ) -> None:
        now = utc_now_iso()
        conn.execute(
            """
            UPDATE documents
            SET status = 'completed',
                error_message = '',
                chunk_count = ?
            WHERE id = ?
            """,
            (chunk_count, document_id),
        )
        conn.execute(
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
        conn.commit()

    def _mark_failed(
        self,
        conn: sqlite3.Connection,
        job_id: str,
        document_id: str,
        error_message: str,
    ) -> None:
        now = utc_now_iso()
        conn.execute(
            """
            UPDATE documents
            SET status = 'failed',
                error_message = ?
            WHERE id = ?
            """,
            (error_message, document_id),
        )
        conn.execute(
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
        conn.commit()
