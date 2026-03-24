from __future__ import annotations

from typing import Any

from docmind.api.schemas import DocumentListItem


def serialize_document_list_item(document: dict[str, Any]) -> dict[str, Any]:
    item = DocumentListItem(
        id=document["id"],
        user_id=document["user_id"],
        kb_id=document["kb_id"],
        file_name=document["file_name"],
        title=document.get("title") or "",
        chunk_count=int(document.get("chunk_count") or 0),
        status=document.get("status") or "",
        error_message=document.get("error_message") or "",
        created_at=document["created_at"],
        kb_name=document.get("kb_name"),
        kb_display_name=document.get("kb_display_name"),
        uploader_name=document.get("uploader_name"),
    )
    return item.model_dump()


def serialize_document_list_items(
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [serialize_document_list_item(document) for document in documents]
