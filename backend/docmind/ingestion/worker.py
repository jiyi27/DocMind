"""Persistent ingestion queue worker backed by SQLite."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from docmind.core import logger
from docmind.db.database import create_sync_connection
from docmind.db.ingestion_queue import IngestionQueueRepository
from docmind.ingestion.graph import ingestion_graph

# Polling interval for checking the ingestion queue
POLL_INTERVAL_SECONDS = 5.0


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

    def _run(self) -> None:
        conn = create_sync_connection()
        queue_repo = IngestionQueueRepository(conn)
        try:
            queue_repo.requeue_processing_jobs()
            while not self._stop_event.is_set():
                job = queue_repo.claim_next_pending_job()
                if job is None:
                    self._stop_event.wait(self.poll_interval)
                    continue

                self._process_job(queue_repo, job)
        finally:
            conn.close()

    def _process_job(
        self, queue_repo: IngestionQueueRepository, job: dict[str, Any]
    ) -> None:
        payload = json.loads(job["payload_json"])
        document_id = job["document_id"]
        file_path = payload["file_path"]

        try:
            result = ingestion_graph.invoke(payload)
            chunk_count = result.get("chunk_count", 0)
            queue_repo.mark_completed(job["id"], document_id, chunk_count)
            logger.info(
                "ingestion_job_completed",
                {
                    "job_id": job["id"],
                    "document_id": document_id,
                    "chunk_count": chunk_count,
                },
            )
        except Exception as exc:
            queue_repo.mark_failed(job["id"], document_id, str(exc))
            logger.error(
                "ingestion_job_failed",
                {"job_id": job["id"], "document_id": document_id},
                exc=exc,
            )
        finally:
            Path(file_path).unlink(missing_ok=True)
