"""
Async SQLite connection management via aiosqlite.
"""

from __future__ import annotations

import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from docmind.db.models import ALL_TABLES

_DB_PATH = "data/docmind.db"
_GLOBAL_CONN: aiosqlite.Connection | None = None


async def init_db() -> None:
    """Create all tables if they don't exist. Called once at app startup."""
    global _GLOBAL_CONN
    if _GLOBAL_CONN is not None:
        return

    _GLOBAL_CONN = await aiosqlite.connect(_DB_PATH)
    _GLOBAL_CONN.row_factory = aiosqlite.Row

    # --- SQLite Optimizations for High Concurrency ---
    await _GLOBAL_CONN.execute("PRAGMA journal_mode = WAL;")
    await _GLOBAL_CONN.execute("PRAGMA synchronous = NORMAL;")
    await _GLOBAL_CONN.execute("PRAGMA foreign_keys = ON;")

    for ddl in ALL_TABLES:
        await _GLOBAL_CONN.execute(ddl)
    await _GLOBAL_CONN.commit()


async def close_db() -> None:
    """Close the global database connection."""
    global _GLOBAL_CONN
    if _GLOBAL_CONN is not None:
        await _GLOBAL_CONN.close()
        _GLOBAL_CONN = None


def get_db_path() -> str:
    """Return the SQLite database path for worker threads and scripts."""
    return _DB_PATH


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that yields the global database connection."""
    if _GLOBAL_CONN is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    # Yield the global connection without closing it
    yield _GLOBAL_CONN
