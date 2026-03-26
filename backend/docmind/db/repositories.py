"""
Data access layer — CRUD operations for all entities.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import aiosqlite

from docmind.core.time import utc_now_iso


def _row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def _parse_sync_job(job: dict[str, Any]) -> dict[str, Any]:
    """Deserialize the JSON ``summary`` field of a sync job row."""
    raw = job.get("summary", "")
    if raw:
        try:
            job["summary"] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            job["summary"] = None
    else:
        job["summary"] = None
    return job


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
        self,
        name: str,
        display_name: str,
        description: str = "",
        embedding_provider: str = "openai_compatible",
        embedding_model: str = "",
        embedding_base_url: str = "",
        embedding_api_key: str = "",
        vector_dimension: int = 0,
    ) -> dict[str, Any]:
        kb_id = str(uuid.uuid4())
        now = utc_now_iso()
        await self.db.execute(
            """
            INSERT INTO knowledge_bases
                (id, name, display_name, description, created_at,
                 embedding_provider, embedding_model, embedding_base_url,
                 embedding_api_key, vector_dimension)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                kb_id,
                name,
                display_name,
                description,
                now,
                embedding_provider,
                embedding_model,
                embedding_base_url,
                embedding_api_key,
                vector_dimension,
            ),
        )
        await self.db.commit()
        return {
            "id": kb_id,
            "name": name,
            "display_name": display_name,
            "description": description,
            "created_at": now,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model,
            "embedding_base_url": embedding_base_url,
            "embedding_api_key": embedding_api_key,
            "vector_dimension": vector_dimension,
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

    async def get_embedding_params(self, kb_name: str) -> dict[str, Any] | None:
        """Return the embedding config columns for a KB, or None if not found."""
        async with self.db.execute(
            "SELECT embedding_provider, embedding_model, embedding_base_url, "
            "embedding_api_key, vector_dimension FROM knowledge_bases WHERE name = ?",
            (kb_name,),
        ) as cur:
            return _row_to_dict(await cur.fetchone())

    async def list_all(self) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM knowledge_bases ORDER BY created_at"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

    async def update_metadata(
        self,
        kb_id: str,
        display_name: str,
        description: str,
    ) -> dict[str, Any] | None:
        await self.db.execute(
            """
            UPDATE knowledge_bases
            SET display_name = ?, description = ?
            WHERE id = ?
            """,
            (display_name, description, kb_id),
        )
        await self.db.commit()
        return await self.get_by_id(kb_id)

    async def update_embedding_connection(
        self,
        kb_id: str,
        embedding_base_url: str,
        embedding_api_key: str,
    ) -> dict[str, Any] | None:
        await self.db.execute(
            """
            UPDATE knowledge_bases
            SET embedding_base_url = ?, embedding_api_key = ?
            WHERE id = ?
            """,
            (embedding_base_url, embedding_api_key, kb_id),
        )
        await self.db.commit()
        return await self.get_by_id(kb_id)

    async def update_confluence_settings(
        self,
        kb_id: str,
        root_page_id: str,
        root_page_title: str,
        sync_enabled: bool,
        sync_interval_minutes: int,
        retrieval_mode: str,
    ) -> dict[str, Any] | None:
        await self.db.execute(
            """
            UPDATE knowledge_bases
            SET confluence_root_page_id = ?,
                confluence_root_page_title = ?,
                confluence_sync_enabled = ?,
                confluence_sync_interval_minutes = ?,
                confluence_retrieval_mode = ?
            WHERE id = ?
            """,
            (
                root_page_id,
                root_page_title,
                int(sync_enabled),
                sync_interval_minutes,
                retrieval_mode,
                kb_id,
            ),
        )
        await self.db.commit()
        return await self.get_by_id(kb_id)

    async def update_sync_status(
        self,
        kb_id: str,
        last_sync_at: str,
        last_sync_status: str,
        last_sync_error: str = "",
    ) -> None:
        await self.db.execute(
            """
            UPDATE knowledge_bases
            SET confluence_last_sync_at = ?,
                confluence_last_sync_status = ?,
                confluence_last_sync_error = ?
            WHERE id = ?
            """,
            (last_sync_at, last_sync_status, last_sync_error, kb_id),
        )
        await self.db.commit()

    async def list_sync_enabled_kbs(self) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM knowledge_bases WHERE confluence_sync_enabled = 1",
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
        user_id: str | None,
        kb_id: str,
        file_name: str,
        title: str = "",
        chunk_count: int = 0,
        doc_id: str | None = None,
        status: str = "pending",
        error_message: str = "",
        file_path: str = "",
        retrieval_mode: str = "chunk",
        source_type: str = "manual",
        external_doc_id: str = "",
        source_url: str = "",
        source_version: int = 0,
    ) -> dict[str, Any]:
        _id = doc_id or str(uuid.uuid4())
        now = utc_now_iso()
        await self.db.execute(
            """
            INSERT INTO documents
                (id, user_id, kb_id, file_name, title, doc_type, chunk_count,
                 status, error_message, file_path, strict_mode, retrieval_mode,
                 source_type, external_doc_id, source_url, source_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _id,
                user_id,
                kb_id,
                file_name,
                title,
                "",
                chunk_count,
                status,
                error_message,
                file_path,
                0,
                retrieval_mode,
                source_type,
                external_doc_id,
                source_url,
                source_version,
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
            "doc_type": "",
            "chunk_count": chunk_count,
            "status": status,
            "error_message": error_message,
            "file_path": file_path,
            "strict_mode": 0,
            "retrieval_mode": retrieval_mode,
            "source_type": source_type,
            "external_doc_id": external_doc_id,
            "source_url": source_url,
            "source_version": source_version,
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

    async def get_by_external_doc_id(
        self, kb_id: str, external_doc_id: str
    ) -> dict[str, Any] | None:
        """Find a Confluence-synced document by its external page ID within a KB."""
        async with self.db.execute(
            "SELECT * FROM documents WHERE kb_id = ? AND external_doc_id = ? AND source_type = 'confluence'",
            (kb_id, external_doc_id),
        ) as cur:
            return _row_to_dict(await cur.fetchone())

    async def list_confluence_docs_by_kb(self, kb_id: str) -> list[dict[str, Any]]:
        """Return all Confluence-synced documents within a KB."""
        async with self.db.execute(
            "SELECT * FROM documents WHERE kb_id = ? AND source_type = 'confluence' ORDER BY created_at DESC",
            (kb_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]

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

    async def delete(self, session_id: str) -> None:
        """Delete a chat session and cascade-delete its messages."""
        await self.db.execute("DELETE FROM chat_sessions WHERE id = ?", (session_id,))
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
        sources_json: str = "[]",
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


# ---------------------------------------------------------------------------
# Sync Job Repository
# ---------------------------------------------------------------------------


class SyncJobRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(
        self,
        kb_id: str,
        trigger_type: str = "manual",
    ) -> dict[str, Any]:
        job_id = str(uuid.uuid4())
        now = utc_now_iso()
        await self.db.execute(
            """
            INSERT INTO kb_sync_jobs
                (id, kb_id, status, trigger_type, error_message,
                 created_at, started_at, finished_at, updated_at)
            VALUES (?, ?, 'pending', ?, '', ?, '', '', ?)
            """,
            (job_id, kb_id, trigger_type, now, now),
        )
        await self.db.commit()
        return _parse_sync_job(
            {
                "id": job_id,
                "kb_id": kb_id,
                "status": "pending",
                "trigger_type": trigger_type,
                "error_message": "",
                "summary": "",
                "created_at": now,
                "started_at": "",
                "finished_at": "",
                "updated_at": now,
            }
        )

    async def get_by_id(self, job_id: str) -> dict[str, Any] | None:
        async with self.db.execute(
            "SELECT * FROM kb_sync_jobs WHERE id = ?", (job_id,)
        ) as cur:
            row = _row_to_dict(await cur.fetchone())
            return _parse_sync_job(row) if row else None

    async def list_by_kb(self, kb_id: str, limit: int = 20) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM kb_sync_jobs WHERE kb_id = ? ORDER BY created_at DESC LIMIT ?",
            (kb_id, limit),
        ) as cur:
            rows = await cur.fetchall()
            return [_parse_sync_job(dict(r)) for r in rows]

    async def get_active_by_kb(self, kb_id: str) -> dict[str, Any] | None:
        async with self.db.execute(
            """
            SELECT *
            FROM kb_sync_jobs
            WHERE kb_id = ? AND status IN ('pending', 'running')
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (kb_id,),
        ) as cur:
            row = _row_to_dict(await cur.fetchone())
            return _parse_sync_job(row) if row else None

    async def update_summary(self, job_id: str, summary: dict[str, Any]) -> None:
        await self.db.execute(
            "UPDATE kb_sync_jobs SET summary = ? WHERE id = ?",
            (json.dumps(summary), job_id),
        )
        await self.db.commit()

    async def update_status(
        self,
        job_id: str,
        status: str,
        error_message: str = "",
    ) -> None:
        now = utc_now_iso()
        fields = {"status": status, "error_message": error_message, "updated_at": now}
        if status == "running":
            fields["started_at"] = now
        elif status in ("completed", "failed"):
            fields["finished_at"] = now

        set_clause = ", ".join(f"{k} = ?" for k in fields)
        await self.db.execute(
            f"UPDATE kb_sync_jobs SET {set_clause} WHERE id = ?",
            (*fields.values(), job_id),
        )
        await self.db.commit()


# ---------------------------------------------------------------------------
# Sync Record Repository
# ---------------------------------------------------------------------------


class SyncRecordRepository:
    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create(
        self,
        job_id: str,
        kb_id: str,
        external_doc_id: str,
        document_title: str,
        source_url: str,
        operation: str,
        status: str,
        error_message: str = "",
    ) -> dict[str, Any]:
        record_id = str(uuid.uuid4())
        now = utc_now_iso()
        await self.db.execute(
            """
            INSERT INTO kb_sync_records
                (id, job_id, kb_id, external_doc_id, document_title,
                 source_url, operation, status, error_message, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                job_id,
                kb_id,
                external_doc_id,
                document_title,
                source_url,
                operation,
                status,
                error_message,
                now,
            ),
        )
        await self.db.commit()
        return {
            "id": record_id,
            "job_id": job_id,
            "kb_id": kb_id,
            "external_doc_id": external_doc_id,
            "document_title": document_title,
            "source_url": source_url,
            "operation": operation,
            "status": status,
            "error_message": error_message,
            "created_at": now,
        }

    async def list_by_job(self, job_id: str) -> list[dict[str, Any]]:
        async with self.db.execute(
            "SELECT * FROM kb_sync_records WHERE job_id = ? ORDER BY created_at ASC",
            (job_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
