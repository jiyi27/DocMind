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
    file_type : str
        Detected file extension (pdf, md).
    metadata : dict
        User-provided metadata (title, url, category, business_line, audience).
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
    file_type: str
    metadata: dict
    documents: list[Document]
    chunks: list[Document]
    status: str
    chunk_count: int
