from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.api.dependencies import get_current_user
from docmind.api.main import app
from docmind.auth.schemas import UserContext


def _override_current_user() -> UserContext:
    return UserContext(
        user_id="user-api-key",
        username="api-tester",
        kb_id="kb-api-key",
        kb_name="kb-api-key",
        role="user",
    )


def _seed_user(db_path: Path) -> None:
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
                "kb-api-key",
                "kb-api-key",
                "KB API Key",
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
            ("user-api-key", "api-tester", "hashed", "kb-api-key", "user", now),
        )
        conn.commit()


def test_api_key_crud_flow() -> None:
    db_path = Path(__file__).resolve().parents[1] / "data" / "test-api-keys.db"
    if db_path.exists():
        db_path.unlink()

    os.environ["DOCMIND_DB_PATH"] = str(db_path)
    app.dependency_overrides[get_current_user] = _override_current_user

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            _seed_user(db_path)

            create_response = client.post(
                "/api-keys",
                json={"name": "Desktop Client", "daily_limit": 123},
            )
            assert create_response.status_code == 200
            create_body = create_response.json()
            assert create_body["code"] == 0
            assert create_body["data"]["raw_key"].startswith("dm_")
            assert create_body["data"]["daily_limit"] == 123
            key_id = create_body["data"]["id"]

            list_response = client.get("/api-keys")
            assert list_response.status_code == 200
            list_body = list_response.json()
            assert list_body["code"] == 0
            assert len(list_body["data"]) == 1
            assert list_body["data"][0]["id"] == key_id
            assert "raw_key" not in list_body["data"][0]

            delete_response = client.delete(f"/api-keys/{key_id}")
            assert delete_response.status_code == 200
            assert delete_response.json()["code"] == 0

            list_after_delete = client.get("/api-keys")
            assert list_after_delete.status_code == 200
            list_after_delete_body = list_after_delete.json()
            assert list_after_delete_body["code"] == 0
            assert list_after_delete_body["data"][0]["is_active"] == 0
    finally:
        app.dependency_overrides.clear()
        os.environ.pop("DOCMIND_DB_PATH", None)
        if db_path.exists():
            db_path.unlink()
