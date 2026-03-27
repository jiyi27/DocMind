"""SQLite connection infrastructure for API, worker threads, and scripts."""

from __future__ import annotations

from contextlib import asynccontextmanager
import os
from pathlib import Path
import sqlite3
from typing import AsyncGenerator

import aiosqlite

from docmind.core.config import settings
from docmind.core.time import utc_now_iso
from docmind.db.models import (
    ALL_INDEXES,
    ALL_TABLES,
    MIGRATE_DOCUMENTS_SOURCE_COLUMNS,
    MIGRATE_KB_SYNC_JOBS_SUMMARY_COLUMN,
    MIGRATE_KNOWLEDGE_BASES_CONFLUENCE_COLUMNS,
    MIGRATE_KNOWLEDGE_BASES_EMBEDDING_COLUMNS,
    MIGRATE_KNOWLEDGE_BASES_ROOT_PAGE_TITLE_COLUMN,
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


async def _bootstrap_system_settings(conn: aiosqlite.Connection) -> None:
    """Seed runtime-editable settings from env defaults when missing in SQLite."""
    seeded_values = {
        "chat_max_messages": str(settings.retrieval.max_messages),
        "retrieval_top_k": str(settings.retrieval.top_k),
    }
    if settings.llm.base_url:
        seeded_values["llm_base_url"] = settings.llm.base_url
    if settings.llm.api_key:
        seeded_values["llm_api_key"] = settings.llm.api_key
    if settings.llm.model:
        seeded_values["llm_model"] = settings.llm.model

    now = utc_now_iso()
    for key, value in seeded_values.items():
        await conn.execute(
            """
            INSERT OR IGNORE INTO system_settings (key, value, updated_at)
            VALUES (?, ?, ?)
            """,
            (key, value, now),
        )


async def _migrate_db(conn: aiosqlite.Connection) -> None:
    """Apply idempotent schema migrations for existing databases."""
    migration_lists = [
        MIGRATE_KNOWLEDGE_BASES_EMBEDDING_COLUMNS,
        MIGRATE_KNOWLEDGE_BASES_CONFLUENCE_COLUMNS,
        MIGRATE_KNOWLEDGE_BASES_ROOT_PAGE_TITLE_COLUMN,
        MIGRATE_DOCUMENTS_SOURCE_COLUMNS,
        MIGRATE_KB_SYNC_JOBS_SUMMARY_COLUMN,
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
    await _GLOBAL_CONN.commit()

    await _migrate_db(_GLOBAL_CONN)
    await _bootstrap_system_settings(_GLOBAL_CONN)
    await _GLOBAL_CONN.commit()


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
