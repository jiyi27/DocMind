"""Ingest router — file upload endpoint for document ingestion."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from docmind.api.schemas import IngestMetadata
from docmind.api.response import ok
from docmind.core.metadata_config import REQUIRED_FIELDS
from docmind.ingestion.graph import ingestion_graph

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("")
async def ingest_document(
    file: UploadFile = File(..., description="PDF or Markdown file to ingest"),
    title: str = Form(default="") if "title" not in REQUIRED_FIELDS else Form(...),
    url: str = Form(default="") if "url" not in REQUIRED_FIELDS else Form(...),
    doc_type: str = (
        Form(..., description="One of: requirement, postmortem, pitfall, sharing, tech_spec")
        if "doc_type" in REQUIRED_FIELDS
        else Form(default="tech_spec", description="One of: requirement, postmortem, pitfall, sharing, tech_spec")
    ),
    business_line: str = (
        Form(..., description="Comma-separated: india, pakistan, all")
        if "business_line" in REQUIRED_FIELDS
        else Form(default="all", description="Comma-separated: india, pakistan, all")
    ),
    service: str = (
        Form(..., description="Comma-separated: collection, risk, admin, all")
        if "service" in REQUIRED_FIELDS
        else Form(default="all", description="Comma-separated: collection, risk, admin, all")
    ),
    department: str = (
        Form(..., description="Comma-separated: backend, qa, ios, android, web, all")
        if "department" in REQUIRED_FIELDS
        else Form(default="all", description="Comma-separated: backend, qa, ios, android, web, all")
    ),
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
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return ok({
        "status": result.get("status", "unknown"),
        "chunk_count": result.get("chunk_count", 0),
        "file_name": file_name,
    })
