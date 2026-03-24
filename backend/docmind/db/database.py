"""SQLite connection infrastructure for API, worker threads, and scripts."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
import sqlite3
from typing import AsyncGenerator

import aiosqlite

from docmind.db.models import (
    ALL_INDEXES,
    ALL_TABLES,
    MIGRATE_DOCUMENTS_SOURCE_COLUMNS,
    MIGRATE_KNOWLEDGE_BASES_CONFLUENCE_COLUMNS,
    MIGRATE_KNOWLEDGE_BASES_EMBEDDING_COLUMNS,
)

_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "docmind.db"
_PRAGMAS = (
    "PRAGMA journal_mode = WAL;",
    "PRAGMA synchronous = NORMAL;",
    "PRAGMA foreign_keys = ON;",
)
_GLOBAL_CONN: aiosqlite.Connection | None = None


def get_db_path() -> str:
    """Return the configured SQLite database path."""
    configured_path = os.getenv("DOCMIND_DB_PATH", "").strip()
    if configured_path:
        return configured_path
    return str(_DEFAULT_DB_PATH)


def _ensure_db_parent_dir(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)


async def _configure_async_connection(conn: aiosqlite.Connection) -> None:
    conn.row_factory = aiosqlite.Row
    for pragma in _PRAGMAS:
        await conn.execute(pragma)


def _configure_sync_connection(conn: sqlite3.Connection) -> None:
    conn.row_factory = sqlite3.Row
    for pragma in _PRAGMAS:
        conn.execute(pragma)


async def create_async_connection() -> aiosqlite.Connection:
    """Create a fully configured aiosqlite connection."""
    db_path = get_db_path()
    _ensure_db_parent_dir(db_path)
    conn = await aiosqlite.connect(db_path)
    await _configure_async_connection(conn)
    return conn


def create_sync_connection() -> sqlite3.Connection:
    """Create a fully configured sqlite3 connection for threads/scripts."""
    db_path = get_db_path()
    _ensure_db_parent_dir(db_path)
    conn = sqlite3.connect(db_path)
    _configure_sync_connection(conn)
    return conn


async def _migrate_db(conn: aiosqlite.Connection) -> None:
    """Apply idempotent schema migrations for existing databases."""
    migration_lists = [
        MIGRATE_KNOWLEDGE_BASES_EMBEDDING_COLUMNS,
        MIGRATE_KNOWLEDGE_BASES_CONFLUENCE_COLUMNS,
        MIGRATE_DOCUMENTS_SOURCE_COLUMNS,
    ]
    for stmts in migration_lists:
        for stmt in stmts:
            try:
                await conn.execute(stmt)
            except Exception:
                # Column already exists — safe to ignore.
                pass

    for stmt in ALL_INDEXES:
        await conn.execute(stmt)
    await conn.commit()


async def init_db() -> None:
    """Create all tables if they don't exist. Called once at app startup."""
    global _GLOBAL_CONN
    if _GLOBAL_CONN is not None:
        return

    _GLOBAL_CONN = await create_async_connection()

    for ddl in ALL_TABLES:
        await _GLOBAL_CONN.execute(ddl)
    for stmt in ALL_INDEXES:
        await _GLOBAL_CONN.execute(stmt)
    await _GLOBAL_CONN.commit()

    await _migrate_db(_GLOBAL_CONN)


async def close_db() -> None:
    """Close the global database connection."""
    global _GLOBAL_CONN
    if _GLOBAL_CONN is not None:
        await _GLOBAL_CONN.close()
        _GLOBAL_CONN = None


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that yields the global database connection."""
    if _GLOBAL_CONN is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")

    # Yield the global connection without closing it
    yield _GLOBAL_CONN
