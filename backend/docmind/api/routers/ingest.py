"""Ingest router — file upload, document listing, and document deletion."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from docmind.api.dependencies import get_current_user
from docmind.api.schemas import IngestMetadata
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.db.database import get_db
from docmind.db.repositories import DocumentRepository, KBRepository
from docmind.ingestion.graph import ingestion_graph
from docmind.vectorstore.qdrant_store import delete_documents_by_doc_id, get_chunks_by_doc_id

router = APIRouter(prefix="/ingest", tags=["ingestion"])


# ---------------------------------------------------------------------------
# POST /ingest/{kb_id}  — upload and ingest a document into a specific KB
# ---------------------------------------------------------------------------

@router.post("/{kb_id}", status_code=status.HTTP_201_CREATED)
async def ingest_document(
    kb_id: str,
    file: UploadFile = File(..., description="PDF or Markdown file to ingest"),
    title: str = Form(default=""),
    url: str = Form(default=""),
    doc_type: str = Form(default="all"),
    service: str = Form(default="all"),
    department: str = Form(default="all"),
    current_user: UserContext = Depends(get_current_user),
):
    """Upload and ingest a document into the specified knowledge base.

    The target knowledge base is identified by ``kb_id`` in the path.
    The caller must be authenticated; any authenticated user may upload
    to any existing knowledge base.
    """
    # Resolve KB name (Qdrant collection slug) from the provided kb_id
    async with get_db() as db:
        kb_repo = KBRepository(db)
        kb = await kb_repo.get_by_id(kb_id)

    if not kb:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

    kb_name = kb["name"]
    file_name = file.filename or "unknown"

    metadata = IngestMetadata(
        title=title or file_name,
        url=url,
        doc_type=doc_type,
        service=service,
        department=department,
    )

    # Pre-generate doc_id so it can be stamped into every Qdrant chunk payload.
    # This allows bulk-deleting all chunks of a document by filtering on doc_id.
    doc_id = str(uuid.uuid4())

    # Write uploaded file to disk temporarily because document loaders
    # (PDF/Markdown parsers) expect file paths, not byte streams.
    suffix = Path(file_name).suffix
    with NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = ingestion_graph.invoke({
            "file_path": tmp_path,
            "metadata": metadata.model_dump(),
            "user_id": current_user.user_id,
            "doc_id": doc_id,
            "kb_name": kb_name,
        })
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    chunk_count = result.get("chunk_count", 0)

    # Persist document record to SQLite using the pre-generated doc_id
    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        doc = await doc_repo.create(
            user_id=current_user.user_id,
            kb_id=kb_id,
            file_name=file_name,
            title=metadata.title,
            doc_type=metadata.doc_type,
            chunk_count=chunk_count,
            doc_id=doc_id,
        )

    return ok(
        data={
            "doc_id": doc["id"],
            "status": result.get("status", "unknown"),
            "chunk_count": chunk_count,
            "file_name": file_name,
            "kb_name": kb_name,
        },
        message="Document ingested successfully",
    )


# ---------------------------------------------------------------------------
# GET /ingest/documents  — list current user's documents
# ---------------------------------------------------------------------------

@router.get("/documents")
async def list_documents(
    current_user: UserContext = Depends(get_current_user),
):
    """Return all documents uploaded by the current user, along with total count."""
    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        docs = await doc_repo.list_by_user(current_user.user_id)
    return ok(data={"total": len(docs), "documents": docs})


# ---------------------------------------------------------------------------
# GET /ingest/documents/kb/{kb_id}  — list current user's docs in a specific KB
# ---------------------------------------------------------------------------

@router.get("/documents/kb/{kb_id}")
async def list_documents_by_kb(
    kb_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Return documents uploaded by the current user within a specific knowledge base.

    If the user is a super admin or an admin of the requested KB, returns
    all documents in the KB with their uploaders. Otherwise, returns only
    documents uploaded by the current user.
    Also returns the total count of matching documents.
    """
    is_super_admin = (current_user.role == "super_admin")
    is_kb_admin = (current_user.role == "admin" and current_user.kb_id == kb_id)

    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        if is_super_admin or is_kb_admin:
            docs = await doc_repo.list_by_kb_with_user_info(kb_id)
        else:
            docs = await doc_repo.list_by_user_and_kb_with_user_info(current_user.user_id, kb_id)

    return ok(data={"total": len(docs), "documents": docs})

# ---------------------------------------------------------------------------
# GET /ingest/{doc_id}/chunks  — inspect chunks of a document
# ---------------------------------------------------------------------------

@router.get("/{doc_id}/chunks")
async def get_document_chunks(
    doc_id: str,
    offset: int = 0,
    limit: int = 20,
    current_user: UserContext = Depends(get_current_user),
):
    """Return paginated chunks (vector store points) for a specific document.

    Useful for verifying that a document was correctly split and ingested.
    Vectors are not returned — only text content and metadata.

    Query params:
    - ``offset``: number of chunks to skip (default 0)
    - ``limit``: max chunks to return, 1-100 (default 20)
    """
    if not (1 <= limit <= 100):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="limit must be between 1 and 100",
        )
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="offset must be >= 0",
        )

    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        doc = await doc_repo.get_by_id(doc_id)

    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc["user_id"] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your document")

    result = get_chunks_by_doc_id(
        kb_name=current_user.kb_name,
        doc_id=doc_id,
        offset=offset,
        limit=limit,
    )

    return ok(data=result)


# ---------------------------------------------------------------------------
# DELETE /ingest/{doc_id}  — delete a document and its vectors
# ---------------------------------------------------------------------------

@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Delete a document record and all its associated Qdrant vectors.

    A document can be deleted by its owner, a super_admin, or the admin of its KB.
    """
    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        doc = await doc_repo.get_by_id(doc_id)

        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

        is_super_admin = current_user.role == "super_admin"
        is_kb_admin = current_user.role == "admin" and current_user.kb_id == doc["kb_id"]
        is_owner = doc["user_id"] == current_user.user_id

        if not (is_owner or is_super_admin or is_kb_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this document")

        # Delete vectors from Qdrant first
        delete_documents_by_doc_id(current_user.kb_name, doc_id)

        # Delete DB record
        await doc_repo.delete(doc_id)

    return ok(
        data={"doc_id": doc_id},
        message="Document deleted successfully",
    )
