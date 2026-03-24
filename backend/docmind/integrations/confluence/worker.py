"""Background Confluence sync worker.

Periodically scans for KBs with ``confluence_sync_enabled = 1`` and
triggers sync for each. Only starts when Confluence is configured.
"""

from __future__ import annotations

import asyncio
import threading

from docmind.core import logger
from docmind.core.config import settings
from docmind.db.database import create_async_connection
from docmind.db.repositories import KBRepository, SyncJobRepository
from docmind.integrations.confluence.service import execute_sync


class ConfluenceSyncWorker:
    """Background thread that periodically syncs Confluence-enabled KBs."""

    def __init__(self, interval_seconds: int | None = None) -> None:
        self.interval = interval_seconds or settings.confluence.sync_interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="docmind-confluence-sync-worker",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "confluence_sync_worker_started",
            {"interval_seconds": self.interval},
        )

    def stop(self, timeout: float = 5.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
        logger.info("confluence_sync_worker_stopped", {})

    def _run(self) -> None:
        loop = asyncio.new_event_loop()
        try:
            while not self._stop_event.is_set():
                try:
                    loop.run_until_complete(self._sync_all_kbs())
                except Exception as exc:
                    logger.error("confluence_sync_worker_error", {}, exc=exc)

                self._stop_event.wait(self.interval)
        finally:
            loop.close()

    async def _sync_all_kbs(self) -> None:
        """Find all sync-enabled KBs and trigger sync for each."""
        conn = await create_async_connection()
        try:
            kb_repo = KBRepository(conn)
            job_repo = SyncJobRepository(conn)

            kbs = await kb_repo.list_sync_enabled_kbs()
            if not kbs:
                return

            logger.info(
                "confluence_sync_worker_cycle",
                {"enabled_kbs": len(kbs)},
            )

            for kb in kbs:
                kb_id = kb["id"]
                try:
                    job = await job_repo.create(kb_id=kb_id, trigger_type="scheduled")
                    await execute_sync(conn, kb_id, job["id"])
                except Exception as exc:
                    logger.error(
                        "confluence_sync_worker_kb_failed",
                        {"kb_id": kb_id},
                        exc=exc,
                    )
        finally:
            await conn.close()
