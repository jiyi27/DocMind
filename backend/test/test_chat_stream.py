from __future__ import annotations

import os
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.api.dependencies import get_current_user
from docmind.api.main import app
from docmind.auth.schemas import UserContext
from docmind.core.exceptions import VectorStoreError


def _override_current_user() -> UserContext:
    return UserContext(
        user_id="test-user",
        username="tester",
        kb_id="kb-test",
        kb_name="india",
        role="user",
    )


def _seed_chat_owner(db_path: Path) -> None:
    now = datetime.now(UTC).isoformat()
    with connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute(
            """
            INSERT INTO knowledge_bases (
                id, name, display_name, description, created_at,
                embedding_provider, embedding_model, embedding_base_url, embedding_api_key, vector_dimension
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "kb-test",
                "india",
                "India KB",
                "",
                now,
                "openai_compatible",
                "",
                "",
                "",
                0,
            ),
        )
        conn.execute(
            """
            INSERT INTO users (id, username, hashed_password, kb_id, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ("test-user", "tester", "hashed", "kb-test", "user", now),
        )
        conn.commit()


def test_chat_stream_returns_sse_error_when_retrieval_fails(monkeypatch) -> None:
    db_path = Path(__file__).resolve().parents[1] / "data" / "test-chat-stream-error.db"
    if db_path.exists():
        db_path.unlink()

    os.environ["DOCMIND_DB_PATH"] = str(db_path)

    async def fake_prepare_rag_stream(**kwargs):
        return type(
            "Prepared",
            (),
            {
                "context": "retrieved context",
                "citations": [
                    {
                        "index": 1,
                        "title": "Test Source",
                        "url": "",
                        "sourceLabel": "[1] Test Source",
                    }
                ],
            },
        )()

    async def fake_stream_rag_completion(**kwargs):
        yield "partial chunk"
        raise VectorStoreError("Embedding model is unavailable.")

    app.dependency_overrides[get_current_user] = _override_current_user
    monkeypatch.setattr(
        "docmind.api.routers.chat.prepare_rag_stream", fake_prepare_rag_stream
    )
    monkeypatch.setattr(
        "docmind.api.routers.chat.stream_rag_completion",
        fake_stream_rag_completion,
    )

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            _seed_chat_owner(db_path)
            session_id = f"session-stream-error-{uuid.uuid4()}"
            with client.stream(
                "POST",
                "/chat/stream",
                json={"chatInput": "hello", "sessionId": session_id},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert '"type": "citations"' in body
        assert '"type": "chunk"' in body
        assert '"type": "error"' in body
        assert "Embedding model is unavailable." in body
        assert "response already started" not in body
    finally:
        app.dependency_overrides.clear()
        os.environ.pop("DOCMIND_DB_PATH", None)
        if db_path.exists():
            db_path.unlink()
