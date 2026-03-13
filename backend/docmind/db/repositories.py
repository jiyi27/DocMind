"""
Data access layer — CRUD operations for all entities.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


# ---------------------------------------------------------------------------
# KnowledgeBase Repository
# ---------------------------------------------------------------------------


class KBRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(self, name: str, display_name: str, description: str = "") -> dict[str, Any]:
        kb_id = str(uuid.uuid4())
        now = _now()
        await self.db.execute(
            "INSERT INTO knowledge_bases (id, name, display_name, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (kb_id, name, display_name, description, now),
        )
        await self.db.commit()
        return {"id": kb_id, "name": name, "display_name": display_name, "description": description, "created_at": now}

    async def get_by_id(self, kb_id: str) -> dict[str, Any] | None:
        async with self.db.execute("SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)) as cur:
            return _row_to_dict(await cur.fetchone())

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        async with self.db.execute("SELECT * FROM knowledge_bases WHERE name = ?", (name,)) as cur:
            return _row_to_dict(await cur.fetchone())

    async def list_all(self) -> list[dict[str, Any]]:
        async with self.db.execute("SELECT * FROM knowledge_bases ORDER BY created_at") as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def delete(self, kb_id: str) -> bool:
        cur = await self.db.execute("DELETE FROM knowledge_bases WHERE id = ?", (kb_id,))
        await self.db.commit()
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# User Repository
# ---------------------------------------------------------------------------


class UserRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(
        self,
        username: str,
        hashed_password: str,
        kb_id: str,
        role: str = "user",
    ) -> dict[str, Any]:
        user_id = str(uuid.uuid4())
        now = _now()
        await self.db.execute(
            "INSERT INTO users (id, username, hashed_password, kb_id, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, hashed_password, kb_id, role, now),
        )
        await self.db.commit()
        return {
            "id": user_id,
            "username": username,
            "kb_id": kb_id,
            "role": role,
            "created_at": now,
        }

    async def get_by_id(self, user_id: str) -> dict[str, Any] | None:
        async with self.db.execute("SELECT * FROM users WHERE id = ?", (user_id,)) as cur:
            return _row_to_dict(await cur.fetchone())

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        async with self.db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cur:
            return _row_to_dict(await cur.fetchone())


# ---------------------------------------------------------------------------
# Document Repository
# ---------------------------------------------------------------------------


class DocumentRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(
        self,
        user_id: str,
        kb_id: str,
        file_name: str,
        title: str = "",
        doc_type: str = "",
        chunk_count: int = 0,
        doc_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a document record.

        Parameters
        ----------
        doc_id:
            Optional explicit UUID. When provided (e.g. pre-generated before
            ingestion so it can be stamped into Qdrant chunk payloads), this
            value is used as the primary key. Otherwise a new UUID is generated.
        """
        _id = doc_id or str(uuid.uuid4())
        now = _now()
        await self.db.execute(
            "INSERT INTO documents (id, user_id, kb_id, file_name, title, doc_type, chunk_count, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (_id, user_id, kb_id, file_name, title, doc_type, chunk_count, now),
        )
        await self.db.commit()
        return {
            "id": _id,
            "user_id": user_id,
            "kb_id": kb_id,
            "file_name": file_name,
            "title": title,
            "doc_type": doc_type,
            "chunk_count": chunk_count,
            "created_at": now,
        }

    async def get_by_id(self, doc_id: str) -> dict[str, Any] | None:
        async with self.db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)) as cur:
            return _row_to_dict(await cur.fetchone())

    async def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_kb(self, kb_id: str) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC", (kb_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_user_and_kb(self, user_id: str, kb_id: str) -> list[dict[str, Any]]:
        """Return all documents uploaded by a specific user within a specific KB."""
        async with self.db.execute(
            "SELECT * FROM documents WHERE user_id = ? AND kb_id = ? ORDER BY created_at DESC",
            (user_id, kb_id),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_kb_with_user_info(self, kb_id: str) -> list[dict[str, Any]]:
        """Return all documents within a specific KB with uploader username."""
        query = """
            SELECT d.*, u.username AS uploader_name
            FROM documents d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.kb_id = ?
            ORDER BY d.created_at DESC
        """
        async with self.db.execute(query, (kb_id,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_user_and_kb_with_user_info(self, user_id: str, kb_id: str) -> list[dict[str, Any]]:
        """Return all documents uploaded by a specific user within a specific KB with uploader username."""
        query = """
            SELECT d.*, u.username AS uploader_name
            FROM documents d
            LEFT JOIN users u ON d.user_id = u.id
            WHERE d.user_id = ? AND d.kb_id = ?
            ORDER BY d.created_at DESC
        """
        async with self.db.execute(query, (user_id, kb_id)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def delete(self, doc_id: str) -> bool:
        cur = await self.db.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        await self.db.commit()
        return cur.rowcount > 0

    async def sum_chunk_count_by_kb(self, kb_id: str) -> int:
        """Return the total number of vector points (chunks) across all documents in a KB."""
        async with self.db.execute(
            "SELECT COALESCE(SUM(chunk_count), 0) FROM documents WHERE kb_id = ?", (kb_id,)
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def delete_by_kb(self, kb_id: str) -> int:
        """Delete all documents belonging to a knowledge base. Returns count deleted."""
        cur = await self.db.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
        await self.db.commit()
        return cur.rowcount
