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
    from docmind.db.database import init_db
    await init_db()

    yield  # App is running
