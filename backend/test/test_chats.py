from __future__ import annotations

import os
import sys
from pathlib import Path
from sqlite3 import connect
from datetime import UTC, datetime

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.api.dependencies import get_current_user
from docmind.api.main import app
from docmind.auth.schemas import UserContext


def _override_current_user() -> UserContext:
    return UserContext(
        user_id="test-user",
        username="tester",
        kb_id="kb-test",
        kb_name="test-kb",
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
                "kb-test",
                "Test KB",
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


def test_delete_chat_session_removes_owned_session() -> None:
    db_path = Path(__file__).resolve().parents[1] / "data" / "test-chats-delete.db"
    if db_path.exists():
        db_path.unlink()

    os.environ["DOCMIND_DB_PATH"] = str(db_path)
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            _seed_chat_owner(db_path)
            create_response = client.post("/chats", json={"title": "Delete me"})
            assert create_response.status_code == 200
            session_id = create_response.json()["data"]["id"]

            delete_response = client.delete(f"/chats/{session_id}")
            assert delete_response.status_code == 200
            assert delete_response.json()["code"] == 0

            detail_response = client.get(f"/chats/{session_id}")
            assert detail_response.status_code == 200
            assert detail_response.json()["code"] == -1
            assert detail_response.json()["message"] == "Chat session not found"
    finally:
        app.dependency_overrides.clear()
        os.environ.pop("DOCMIND_DB_PATH", None)
        if db_path.exists():
            db_path.unlink()
