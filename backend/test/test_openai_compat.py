from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from sqlite3 import connect

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.api.main import app
from docmind.auth.api_key import hash_api_key


RAW_API_KEY = "dm_test_openai_compat_key"


def _seed_data(db_path: Path) -> None:
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
                "kb-openai",
                "kb-openai",
                "KB OpenAI Compat",
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
            ("user-openai", "openai-user", "hashed", "kb-openai", "user", now),
        )
        conn.execute(
            """
            INSERT INTO api_keys (
                id, user_id, key_hash, key_prefix, name, daily_limit,
                is_active, created_at, last_used_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (
                "api-key-openai",
                "user-openai",
                hash_api_key(RAW_API_KEY),
                RAW_API_KEY[:12],
                "Compat Test Key",
                1000,
                now,
                "",
            ),
        )
        conn.commit()


def test_openai_compat_non_stream_completion(monkeypatch) -> None:
    db_path = Path(__file__).resolve().parents[1] / "data" / "test-openai-compat.db"
    if db_path.exists():
        db_path.unlink()

    os.environ["DOCMIND_DB_PATH"] = str(db_path)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            _seed_data(db_path)

            monkeypatch.setattr(
                "docmind.api.routers.openai_compat.get_llm_runtime_settings",
                lambda: type("Runtime", (), {"model": "runtime-model"})(),
            )

            async def fake_run_rag_completion(**kwargs):
                return type(
                    "Result",
                    (),
                    {
                        "answer": f"Answer: {kwargs['query']}",
                        "sources": ["[1] Test Source"],
                    },
                )()

            monkeypatch.setattr(
                "docmind.api.routers.openai_compat.run_rag_completion",
                fake_run_rag_completion,
            )

            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {RAW_API_KEY}"},
                json={
                    "model": "ignored-by-runtime",
                    "messages": [
                        {"role": "system", "content": "Be concise."},
                        {"role": "user", "content": "What is DocMind?"},
                    ],
                },
            )

        assert response.status_code == 200
        body = response.json()
        assert body["object"] == "chat.completion"
        assert body["model"] == "runtime-model"
        assert body["choices"][0]["message"]["role"] == "assistant"
        assert body["choices"][0]["message"]["content"] == "Answer: What is DocMind?"
        assert body["sources"] == ["[1] Test Source"]
    finally:
        os.environ.pop("DOCMIND_DB_PATH", None)
        if db_path.exists():
            db_path.unlink()


def test_openai_compat_stream_completion(monkeypatch) -> None:
    db_path = (
        Path(__file__).resolve().parents[1] / "data" / "test-openai-compat-stream.db"
    )
    if db_path.exists():
        db_path.unlink()

    os.environ["DOCMIND_DB_PATH"] = str(db_path)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            _seed_data(db_path)

            monkeypatch.setattr(
                "docmind.api.routers.openai_compat.get_llm_runtime_settings",
                lambda: type("Runtime", (), {"model": "runtime-model"})(),
            )

            async def fake_prepare_rag_stream(**kwargs):
                return type(
                    "Prepared",
                    (),
                    {
                        "context": "retrieved context",
                        "sources": ["[1] Stream Source"],
                    },
                )()

            async def fake_stream_rag_completion(**kwargs):
                yield "hello "
                yield "world"

            monkeypatch.setattr(
                "docmind.api.routers.openai_compat.prepare_rag_stream",
                fake_prepare_rag_stream,
            )
            monkeypatch.setattr(
                "docmind.api.routers.openai_compat.stream_rag_completion",
                fake_stream_rag_completion,
            )

            with client.stream(
                "POST",
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {RAW_API_KEY}"},
                json={
                    "model": "ignored-by-runtime",
                    "stream": True,
                    "messages": [{"role": "user", "content": "Stream please"}],
                },
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert '"object": "chat.completion.chunk"' in body
        assert '"role": "assistant"' in body
        assert '"content": "hello "' in body
        assert '"content": "world"' in body
        assert '"sources": ["[1] Stream Source"]' in body
        assert "data: [DONE]" in body
    finally:
        os.environ.pop("DOCMIND_DB_PATH", None)
        if db_path.exists():
            db_path.unlink()


def test_openai_compat_rejects_missing_user_message() -> None:
    db_path = (
        Path(__file__).resolve().parents[1] / "data" / "test-openai-compat-invalid.db"
    )
    if db_path.exists():
        db_path.unlink()

    os.environ["DOCMIND_DB_PATH"] = str(db_path)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            _seed_data(db_path)

            response = client.post(
                "/v1/chat/completions",
                headers={"Authorization": f"Bearer {RAW_API_KEY}"},
                json={
                    "model": "runtime-model",
                    "messages": [{"role": "assistant", "content": "No user turn"}],
                },
            )

        assert response.status_code == 400
        body = response.json()
        assert body["error"]["type"] == "invalid_request_error"
        assert "user message" in body["error"]["message"]
    finally:
        os.environ.pop("DOCMIND_DB_PATH", None)
        if db_path.exists():
            db_path.unlink()
