from __future__ import annotations

import sys
import uuid
from pathlib import Path

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


def test_chat_stream_returns_sse_error_when_retrieval_fails(monkeypatch) -> None:
    def fake_retrieve(query: str, kb_name: str) -> tuple[str, list[str]]:
        return ("retrieved context", ["[1] Test Source"])

    async def fake_stream_generate(**kwargs):
        yield "partial chunk"
        raise VectorStoreError("Embedding model is unavailable.")

    app.dependency_overrides[get_current_user] = _override_current_user
    monkeypatch.setattr("docmind.api.routers.chat.retrieve", fake_retrieve)
    monkeypatch.setattr(
        "docmind.api.routers.chat.stream_generate", fake_stream_generate
    )

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            session_id = f"session-stream-error-{uuid.uuid4()}"
            with client.stream(
                "POST",
                "/chat/stream",
                json={"chatInput": "hello", "sessionId": session_id},
            ) as response:
                body = "".join(response.iter_text())

        assert response.status_code == 200
        assert '"type": "sources"' in body
        assert '"type": "chunk"' in body
        assert '"type": "error"' in body
        assert "Embedding model is unavailable." in body
        assert "response already started" not in body
    finally:
        app.dependency_overrides.clear()
