"""Ingestion pipeline state definition."""

from __future__ import annotations

from typing import TypedDict

from langchain_core.documents import Document


class IngestionState(TypedDict, total=False):
    """State flowing through the ingestion graph.

    Attributes
    ----------
    file_path : str
        Path to the file to ingest.
    metadata : dict
        User-provided metadata (title, url, doc_type, service, department).
    user_id : str
        ID of the user who uploaded the document.
    doc_id : str
        UUID assigned to this document record — stamped into every chunk's
        payload so that all chunks can be deleted by filtering on doc_id.
    kb_name : str
        Knowledge base slug (e.g. "india") used to select the Qdrant collection.
    documents : list[Document]
        Raw loaded documents.
    chunks : list[Document]
        Documents after text splitting.
    status : str
        Final status of the ingestion ("success" / "error").
    chunk_count : int
        Number of chunks stored.
    """

    file_path: str
    metadata: dict
    user_id: str
    doc_id: str
    kb_name: str
    documents: list[Document]
    chunks: list[Document]
    status: str
    chunk_count: int
