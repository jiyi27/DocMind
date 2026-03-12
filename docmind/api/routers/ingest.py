"""Ingest router — file upload endpoint for document ingestion."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from docmind.api.schemas import IngestMetadata, IngestResponse
from docmind.core import logger
from docmind.ingestion.graph import ingestion_graph

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("", response_model=IngestResponse)
async def ingest_document(
    file: UploadFile = File(..., description="PDF or Markdown file to ingest"),
    title: str = Form(default=""),
    url: str = Form(default=""),
    doc_type: str = Form(default="tech_spec", description="One of: requirement, postmortem, pitfall, sharing, tech_spec"),
    business_line: str = Form(default="all", description="Comma-separated: india, pakistan, all"),
    service: str = Form(default="all", description="Comma-separated: collection, risk, admin, all"),
    department: str = Form(default="all", description="Comma-separated: backend, qa, ios, android, web, all"),
):
    """Upload and ingest a document into the knowledge base.

    Accepts .pdf and .md files, along with optional metadata.
    """
    file_name = file.filename or "unknown"

    metadata = IngestMetadata(
        title=title or file_name,
        url=url,
        doc_type=doc_type,
        business_line=business_line,
        service=service,
        department=department,
    )

    # Write uploaded file to a temp location for processing
    suffix = Path(file_name).suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = ingestion_graph.invoke({
            "file_path": tmp_path,
            "metadata": metadata.model_dump(),
        })
    except Exception as exc:
        logger.error("ingest_failed", {
            "file_name": file_name,
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        raise HTTPException(
            status_code=500,
            detail="Failed to ingest the document. Please check the file and try again.",
        ) from exc
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return IngestResponse(
        status=result.get("status", "unknown"),
        chunk_count=result.get("chunk_count", 0),
        file_name=file_name,
    )
