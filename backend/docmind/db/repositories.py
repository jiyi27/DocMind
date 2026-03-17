"""
Data access layer — CRUD operations for all entities.
"""

from __future__ import annotations

import uuid
from typing import Any

import aiosqlite

from docmind.core.time import utc_now_iso


def _row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _document_list_query(where_clause: str) -> str:
    return f"""
        SELECT
            d.*,
            k.name AS kb_name,
            k.display_name AS kb_display_name,
            u.username AS uploader_name
        FROM documents d
        LEFT JOIN knowledge_bases k ON d.kb_id = k.id
        LEFT JOIN users u ON d.user_id = u.id
        WHERE {where_clause}
        ORDER BY d.created_at DESC
    """


# ---------------------------------------------------------------------------
# KnowledgeBase Repository
# ---------------------------------------------------------------------------


class KBRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(
        self, name: str, display_name: str, description: str = ""
    ) -> dict[str, Any]:
        kb_id = str(uuid.uuid4())
        now = utc_now_iso()
        await self.db.execute(
            "INSERT INTO knowledge_bases (id, name, display_name, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (kb_id, name, display_name, description, now),
        )
        await self.db.commit()
        return {
            "id": kb_id,
            "name": name,
            "display_name": display_name,
            "description": description,
            "created_at": now,
        }

    async def get_by_id(self, kb_id: str) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM knowledge_bases WHERE id = ?", (kb_id,)
        ) as cur:
            return _row_to_dict(await cur.fetchone())

    async def get_by_name(self, name: str) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM knowledge_bases WHERE name = ?", (name,)
        ) as cur:
            return _row_to_dict(await cur.fetchone())

    async def list_all(self) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM knowledge_bases ORDER BY created_at"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def delete(self, kb_id: str) -> bool:
        cur = await self.db.execute(
            "DELETE FROM knowledge_bases WHERE id = ?", (kb_id,)
        )
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
        now = utc_now_iso()
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
        async with self.db.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ) as cur:
            return _row_to_dict(await cur.fetchone())

    async def get_by_username(self, username: str) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ) as cur:
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
        status: str = "pending",
        error_message: str = "",
        file_path: str = "",
        strict_mode: bool = True,
    ) -> dict[str, Any]:
        """Create a document record.

        Parameters
        ----------
        user_id : str
        kb_id : str
        file_name : str
        title : str
        doc_type : str
        chunk_count : int
        doc_id : str
        status : str
        error_message : str
        file_path : str
        strict_mode : bool
        """
        _id = doc_id or str(uuid.uuid4())
        now = utc_now_iso()
        strict_int = 1 if strict_mode else 0
        await self.db.execute(
            """
            INSERT INTO documents (id, user_id, kb_id, file_name, title, doc_type, chunk_count, status, error_message, file_path, strict_mode, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _id,
                user_id,
                kb_id,
                file_name,
                title,
                doc_type,
                chunk_count,
                status,
                error_message,
                file_path,
                strict_int,
                now,
            ),
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
            "status": status,
            "error_message": error_message,
            "file_path": file_path,
            "strict_mode": strict_int,
            "created_at": now,
        }

    async def update_status(
        self,
        doc_id: str,
        status: str,
        error_message: str = "",
        chunk_count: int | None = None,
    ) -> None:
        """Update the processing status of a document."""
        if chunk_count is not None:
            await self.db.execute(
                "UPDATE documents SET status = ?, error_message = ?, chunk_count = ? WHERE id = ?",
                (status, error_message, chunk_count, doc_id),
            )
        else:
            await self.db.execute(
                "UPDATE documents SET status = ?, error_message = ? WHERE id = ?",
                (status, error_message, doc_id),
            )
        await self.db.commit()

    async def get_by_id(self, doc_id: str) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        ) as cur:
            return _row_to_dict(await cur.fetchone())

    async def get_by_id_with_display_info(self, doc_id: str) -> dict[str, Any] | None:
        query = _document_list_query("d.id = ?")
        async with self.db.execute(query, (doc_id,)) as cur:
            return _row_to_dict(await cur.fetchone())

    async def list_by_user(self, user_id: str) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_user_with_kb_info(self, user_id: str) -> list[dict[str, Any]]:
        """Return all documents uploaded by a specific user across all KBs, with KB display name."""
        query = _document_list_query("d.user_id = ?")
        async with self.db.execute(query, (user_id,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_kb(self, kb_id: str) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM documents WHERE kb_id = ? ORDER BY created_at DESC", (kb_id,)
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_user_and_kb(
        self, user_id: str, kb_id: str
    ) -> list[dict[str, Any]]:
        """Return all documents uploaded by a specific user within a specific KB."""
        async with self.db.execute(
            "SELECT * FROM documents WHERE user_id = ? AND kb_id = ? ORDER BY created_at DESC",
            (user_id, kb_id),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_kb_with_user_info(self, kb_id: str) -> list[dict[str, Any]]:
        """Return all documents within a specific KB with uploader username."""
        query = _document_list_query("d.kb_id = ?")
        async with self.db.execute(query, (kb_id,)) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def list_by_user_and_kb_with_user_info(
        self, user_id: str, kb_id: str
    ) -> list[dict[str, Any]]:
        """Return all documents uploaded by a specific user within a specific KB with uploader username."""
        query = _document_list_query("d.user_id = ? AND d.kb_id = ?")
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
            "SELECT COALESCE(SUM(chunk_count), 0) FROM documents WHERE kb_id = ?",
            (kb_id,),
        ) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def delete_by_kb(self, kb_id: str) -> int:
        """Delete all documents belonging to a knowledge base. Returns count deleted."""
        cur = await self.db.execute("DELETE FROM documents WHERE kb_id = ?", (kb_id,))
        await self.db.commit()
        return cur.rowcount


# ---------------------------------------------------------------------------
# Ingestion Job Repository
# ---------------------------------------------------------------------------


class IngestionJobRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create_pending(
        self,
        document_id: str,
        payload_json: str,
    ) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = utc_now_iso()
        await self.db.execute(
            """
            INSERT INTO ingestion_jobs (
                id,
                document_id,
                payload_json,
                status,
                attempt_count,
                error_message,
                claimed_at,
                started_at,
                finished_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, 'pending', 0, '', '', '', '', ?, ?)
            """,
            (job_id, document_id, payload_json, now, now),
        )
        await self.db.commit()
        return {
            "id": job_id,
            "document_id": document_id,
            "payload_json": payload_json,
            "status": "pending",
            "attempt_count": 0,
            "error_message": "",
            "claimed_at": "",
            "started_at": "",
            "finished_at": "",
            "created_at": now,
            "updated_at": now,
        }

    async def get_by_document_id(self, document_id: str) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM ingestion_jobs WHERE document_id = ?",
            (document_id,),
        ) as cur:
            return _row_to_dict(await cur.fetchone())


# ---------------------------------------------------------------------------
# Chat Session Repository
# ---------------------------------------------------------------------------


class ChatSessionRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(
        self,
        user_id: str,
        title: str,
        kb_id: str | None = None,
        status: str = "active",
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a chat session record."""
        chat_id = session_id or str(uuid.uuid4())
        now = utc_now_iso()
        await self.db.execute(
            """
            INSERT INTO chat_sessions (id, user_id, kb_id, title, status, message_count, last_message_at, last_message_preview, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (chat_id, user_id, kb_id, title, status, 0, None, "", now, now),
        )
        await self.db.commit()
        return {
            "id": chat_id,
            "user_id": user_id,
            "kb_id": kb_id,
            "title": title,
            "status": status,
            "message_count": 0,
            "last_message_at": None,
            "last_message_preview": "",
            "created_at": now,
            "updated_at": now,
        }

    async def get_by_id(self, session_id: str) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM chat_sessions WHERE id = ?", (session_id,)
        ) as cur:
            return _row_to_dict(await cur.fetchone())

    async def list_by_user(
        self,
        user_id: str,
        kb_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if kb_id:
            query = """
                SELECT * FROM chat_sessions
                WHERE user_id = ? AND kb_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """
            params = (user_id, kb_id, limit, offset)
        else:
            query = """
                SELECT * FROM chat_sessions
                WHERE user_id = ?
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """
            params = (user_id, limit, offset)
        async with self.db.execute(query, params) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def count_by_user(self, user_id: str, kb_id: str | None = None) -> int:
        if kb_id:
            query = "SELECT COUNT(*) FROM chat_sessions WHERE user_id = ? AND kb_id = ?"
            params = (user_id, kb_id)
        else:
            query = "SELECT COUNT(*) FROM chat_sessions WHERE user_id = ?"
            params = (user_id,)
        async with self.db.execute(query, params) as cur:
            row = await cur.fetchone()
            return int(row[0]) if row else 0

    async def touch(
        self,
        session_id: str,
        message_count_delta: int = 0,
        last_message_preview: str | None = None,
    ) -> None:
        """Update session activity timestamps and optional message count/preview."""
        now = utc_now_iso()
        if last_message_preview is None:
            await self.db.execute(
                """
                UPDATE chat_sessions
                SET updated_at = ?, last_message_at = ?, message_count = message_count + ?
                WHERE id = ?
                """,
                (now, now, message_count_delta, session_id),
            )
        else:
            await self.db.execute(
                """
                UPDATE chat_sessions
                SET updated_at = ?, last_message_at = ?, message_count = message_count + ?, last_message_preview = ?
                WHERE id = ?
                """,
                (now, now, message_count_delta, last_message_preview, session_id),
            )
        await self.db.commit()

    async def update_title(self, session_id: str, title: str) -> None:
        """Overwrite the session title (used after async LLM title generation)."""
        now = utc_now_iso()
        await self.db.execute(
            "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
            (title, now, session_id),
        )
        await self.db.commit()


# ---------------------------------------------------------------------------
# Chat Message Repository
# ---------------------------------------------------------------------------


class ChatMessageRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(
        self,
        session_id: str,
        role: str,
        content: str,
        sources_json: str = "",
        model_name: str = "",
        token_count: int = 0,
        message_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a chat message record."""
        _id = message_id or str(uuid.uuid4())
        now = utc_now_iso()
        await self.db.execute(
            """
            INSERT INTO chat_messages (id, session_id, role, content, sources_json, model_name, token_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _id,
                session_id,
                role,
                content,
                sources_json,
                model_name,
                token_count,
                now,
            ),
        )
        await self.db.commit()
        return {
            "id": _id,
            "session_id": session_id,
            "role": role,
            "content": content,
            "sources_json": sources_json,
            "model_name": model_name,
            "token_count": token_count,
            "created_at": now,
        }

    async def list_by_session(self, session_id: str) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
