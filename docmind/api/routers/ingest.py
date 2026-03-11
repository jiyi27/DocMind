"""Ingest router — file upload endpoint for document ingestion."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, UploadFile

from docmind.api.schemas import IngestMetadata, IngestResponse
from docmind.ingestion.graph import ingestion_graph

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(..., description="PDF or Markdown file to ingest"),
    title: str = Form(default=""),
    url: str = Form(default=""),
    category: str = Form(default="none"),
    business_line: str = Form(default="none"),
    audience: str = Form(default="all"),
):
    """Upload and ingest a document into the knowledge base.

    Accepts .pdf and .md files, along with optional metadata.
    Mirrors the n8n "On form submission" trigger.
    """
    metadata = IngestMetadata(
        title=title or file.filename or "",
        url=url,
        category=category,
        business_line=business_line,
        audience=audience,
    )

    # Write uploaded file to a temp location for processing
    suffix = Path(file.filename or "doc.pdf").suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = ingestion_graph.invoke({
            "file_path": tmp_path,
            "metadata": metadata.model_dump(),
        })
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return IngestResponse(
        status=result.get("status", "unknown"),
        chunk_count=result.get("chunk_count", 0),
        file_name=file.filename or "unknown",
    )
