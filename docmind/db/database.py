"""
Async SQLite connection management via aiosqlite.
"""

import aiosqlite
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from docmind.db.models import ALL_TABLES

_DB_PATH = "docmind.db"


async def init_db() -> None:
    """Create all tables if they don't exist. Called once at app startup."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        for ddl in ALL_TABLES:
            await db.execute(ddl)
        await db.commit()


@asynccontextmanager
async def get_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager that yields a database connection."""
    async with aiosqlite.connect(_DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON;")
        yield db
