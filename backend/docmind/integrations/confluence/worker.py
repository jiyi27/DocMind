"""Background Confluence sync worker.

Periodically scans for KBs with ``confluence_sync_enabled = 1`` and
triggers sync for each. Runtime Confluence configuration is validated
when KB sync is enabled and again when a sync actually runs.
"""

from __future__ import annotations

import asyncio
import threading
from datetime import datetime, timedelta, timezone

from docmind.core import logger
from docmind.db.database import create_async_connection
from docmind.db.repositories import KBRepository, SyncJobRepository
from docmind.integrations.confluence.service import execute_sync

POLL_INTERVAL_SECONDS = 60.0


class ConfluenceSyncWorker:
    """Background thread that periodically syncs Confluence-enabled KBs."""

    def __init__(self, poll_interval_seconds: float = POLL_INTERVAL_SECONDS) -> None:
        self.poll_interval_seconds = poll_interval_seconds
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
            {"poll_interval_seconds": self.poll_interval_seconds},
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

                self._stop_event.wait(self.poll_interval_seconds)
        finally:
            loop.close()

    def _is_sync_due(self, kb: dict[str, object]) -> bool:
        last_sync_at = str(kb.get("confluence_last_sync_at") or "").strip()
        if not last_sync_at:
            return True

        interval_minutes = max(int(kb.get("confluence_sync_interval_minutes") or 5), 5)
        try:
            last_sync_dt = datetime.fromisoformat(last_sync_at)
        except ValueError:
            return True

        if last_sync_dt.tzinfo is None:
            last_sync_dt = last_sync_dt.replace(tzinfo=timezone.utc)

        next_sync_at = last_sync_dt + timedelta(minutes=interval_minutes)
        return datetime.now(timezone.utc) >= next_sync_at

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
                    active_job = await job_repo.get_active_by_kb(kb_id)
                    if active_job:
                        continue

                    if not self._is_sync_due(kb):
                        continue

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
