"""Application lifespan: startup validation and resource initialization."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from docmind.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks and initialize resources before accepting requests."""
    missing = settings.validate()
    if missing:
        print(
            "[STARTUP ERROR] The following required environment variables are missing or invalid:\n"
            + "".join(f"  - {var}\n" for var in missing)
            + "Please set them in your .env file or environment and restart the application.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize SQLite database (creates tables if they don't exist)
    from docmind.db.database import close_db, init_db
    from docmind.ingestion.worker import IngestionQueueWorker
    from docmind.integrations.confluence.worker import ConfluenceSyncWorker
    from docmind.services.system_settings import initialize_runtime_settings_cache

    await init_db()
    initialize_runtime_settings_cache()
    worker = IngestionQueueWorker()
    worker.start()

    confluence_worker = ConfluenceSyncWorker()
    confluence_worker.start()

    yield  # App is running

    # Cleanup resources on shutdown
    confluence_worker.stop()
    worker.stop()
    await close_db()
