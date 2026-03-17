from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.api.serializers import serialize_document_list_item


def test_serialize_document_list_item_returns_uniform_shape() -> None:
    raw_document = {
        "id": "doc-1",
        "user_id": "user-1",
        "kb_id": "kb-1",
        "file_name": "guide.md",
        "title": "Guide",
        "doc_type": "manual",
        "chunk_count": 3,
        "status": "pending",
        "error_message": "",
        "created_at": "2026-03-17T00:00:00+00:00",
        "strict_mode": 1,
        "kb_name": "support",
        "kb_display_name": "Support KB",
        "uploader_name": None,
    }

    serialized = serialize_document_list_item(raw_document)

    assert serialized == {
        "id": "doc-1",
        "user_id": "user-1",
        "kb_id": "kb-1",
        "file_name": "guide.md",
        "title": "Guide",
        "doc_type": "manual",
        "chunk_count": 3,
        "status": "pending",
        "error_message": "",
        "created_at": "2026-03-17T00:00:00+00:00",
        "strict_mode": True,
        "kb_name": "support",
        "kb_display_name": "Support KB",
        "uploader_name": None,
    }
