"""Ingest router — file upload, document listing, and document deletion."""

from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse

from docmind.api.dependencies import get_current_user
from docmind.api.schemas import IngestMetadata
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.db.database import get_db
from docmind.db.repositories import DocumentRepository, KBRepository
from docmind.ingestion.graph import ingestion_graph
from docmind.vectorstore.qdrant_store import (
    delete_documents_by_doc_id,
    get_chunks_by_doc_id,
)

router = APIRouter(prefix="/ingest", tags=["ingestion"])


# ---------------------------------------------------------------------------
# POST /ingest/{kb_id}  — upload and ingest a document into a specific KB
# ---------------------------------------------------------------------------


async def process_document_task(
    doc_id: str,
    file_path: str,
    metadata_dict: dict,
    user_id: str,
    kb_name: str,
    strict_mode: bool,
    chunk_size: int,
    max_chunk_size: int,
):
    """Background task to run the ingestion graph."""
    try:
        async with get_db() as db:
            doc_repo = DocumentRepository(db)
            await doc_repo.update_status(doc_id, "processing")

        result = ingestion_graph.invoke(
            {
                "file_path": file_path,
                "metadata": metadata_dict,
                "user_id": user_id,
                "doc_id": doc_id,
                "kb_name": kb_name,
                "strict_mode": strict_mode,
                "chunk_size": chunk_size,
                "max_chunk_size": max_chunk_size,
            }
        )

        chunk_count = result.get("chunk_count", 0)
        async with get_db() as db:
            doc_repo = DocumentRepository(db)
            await doc_repo.update_status(doc_id, "completed", chunk_count=chunk_count)

    except Exception as e:
        async with get_db() as db:
            doc_repo = DocumentRepository(db)
            await doc_repo.update_status(doc_id, "failed", error_message=str(e))
    finally:
        Path(file_path).unlink(missing_ok=True)


@router.post(
    "/{kb_id}",
    status_code=status.HTTP_201_CREATED,
    summary="Upload and Ingest Document",
)
async def ingest_document(
    kb_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF or Markdown file to ingest"),
    title: str = Form(default=""),
    url: str = Form(default=""),
    doc_type: str = Form(default="all"),
    service: str = Form(default="all"),
    department: str = Form(default="all"),
    strict_mode: bool = Form(
        default=True, description="Enable strict chunking validation"
    ),
    chunk_size: int = Form(default=500, description="Target chunk size"),
    max_chunk_size: int = Form(
        default=1500, description="Max allowed chunk size for code blocks"
    ),
    current_user: UserContext = Depends(get_current_user),
):
    """Upload a PDF or Markdown file to a specific KB, extract text, and store in the vector database."""
    # Resolve KB name (Qdrant collection slug) from the provided kb_id
    async with get_db() as db:
        kb_repo = KBRepository(db)
        kb = await kb_repo.get_by_id(kb_id)

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )

    kb_name = kb["name"]
    file_name = file.filename or "unknown"

    metadata = IngestMetadata(
        title=title or file_name,
        url=url,
        doc_type=doc_type,
        service=service,  # type: ignore
        department=department,  # type: ignore
        strict_mode=strict_mode,
        chunk_size=chunk_size,
        max_chunk_size=max_chunk_size,
    )

    doc_id = str(uuid.uuid4())

    # Write uploaded file to disk temporarily because document loaders
    # (PDF/Markdown parsers) expect file paths, not byte streams.
    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = upload_dir / f"{doc_id}_{file_name}"

    content = await file.read()
    with open(tmp_path, "wb") as f:
        f.write(content)

    # Persist document record to SQLite as pending
    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        doc = await doc_repo.create(
            user_id=current_user.user_id,
            kb_id=kb_id,
            file_name=file_name,
            title=metadata.title,
            doc_type=metadata.doc_type,
            chunk_count=0,
            doc_id=doc_id,
            status="pending",
            file_path=str(tmp_path),
            strict_mode=strict_mode,
        )

    # Add background task
    background_tasks.add_task(
        process_document_task,
        doc_id=doc_id,
        file_path=str(tmp_path),
        metadata_dict=metadata.model_dump(),
        user_id=current_user.user_id,
        kb_name=kb_name,
        strict_mode=strict_mode,
        chunk_size=chunk_size,
        max_chunk_size=max_chunk_size,
    )

    return ok(
        data={
            "doc_id": doc["id"],
            "status": "pending",
            "chunk_count": 0,
            "file_name": file_name,
            "kb_name": kb_name,
        },
        message="Document uploaded and ingestion queued",
    )


# ---------------------------------------------------------------------------
# GET /ingest/documents  — list current user's documents
# ---------------------------------------------------------------------------


@router.get("/documents", summary="List All User Documents")
async def list_documents(
    current_user: UserContext = Depends(get_current_user),
):
    """Return a list of document records uploaded by the current user across all knowledge bases."""
    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        docs = await doc_repo.list_by_user_with_kb_info(current_user.user_id)
    return ok(data={"total": len(docs), "documents": docs})


# ---------------------------------------------------------------------------
# GET /ingest/documents/kb/{kb_id}  — list current user's docs in a specific KB
# ---------------------------------------------------------------------------


@router.get("/documents/kb/{kb_id}", summary="List Documents by KB")
async def list_documents_by_kb(
    kb_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Return document records within a specific KB (Admins see all, regular users see only theirs)."""
    is_super_admin = current_user.role == "super_admin"
    is_kb_admin = current_user.role == "admin" and current_user.kb_id == kb_id

    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        if is_super_admin or is_kb_admin:
            docs = await doc_repo.list_by_kb_with_user_info(kb_id)
        else:
            docs = await doc_repo.list_by_user_and_kb_with_user_info(
                current_user.user_id, kb_id
            )

    return ok(data={"total": len(docs), "documents": docs})


# ---------------------------------------------------------------------------
# GET /ingest/documents/{doc_id}  — get a single document's metadata
# ---------------------------------------------------------------------------


@router.get("/documents/{doc_id}", summary="Get Document Detail")
async def get_document(
    doc_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Return metadata for a single document."""
    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        doc = await doc_repo.get_by_id(doc_id)

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    async with get_db() as db:
        kb_repo = KBRepository(db)
        kb = await kb_repo.get_by_id(doc["kb_id"])

    return ok(
        data={
            **doc,
            "kb_display_name": kb["display_name"] if kb else None,
            "kb_name": kb["name"] if kb else None,
        }
    )


# ---------------------------------------------------------------------------
# GET /ingest/{doc_id}/chunks  — inspect chunks of a document
# ---------------------------------------------------------------------------


@router.get("/{doc_id}/chunks", summary="Inspect Document Chunks")
async def get_document_chunks(
    doc_id: str,
    offset: int = 0,
    limit: int = 20,
    current_user: UserContext = Depends(get_current_user),
):
    """Examine text chunks and metadata of a specific document after splitting for validation."""
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
        kb_repo = KBRepository(db)
        doc = await doc_repo.get_by_id(doc_id)
        kb = await kb_repo.get_by_id(doc["kb_id"]) if doc else None

    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    if not kb:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )

    result = get_chunks_by_doc_id(
        kb_name=kb["name"],
        doc_id=doc_id,
        offset=offset,
        limit=limit,
    )

    return ok(data=result)


# ---------------------------------------------------------------------------
# DELETE /ingest/{doc_id}  — delete a document and its vectors
# ---------------------------------------------------------------------------


@router.delete("/{doc_id}", summary="Delete Document")
async def delete_document(
    doc_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    """Permanently remove a document and its associated vector chunks from the database and vector store."""
    async with get_db() as db:
        doc_repo = DocumentRepository(db)
        doc = await doc_repo.get_by_id(doc_id)

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
            )

        is_super_admin = current_user.role == "super_admin"
        is_kb_admin = (
            current_user.role == "admin" and current_user.kb_id == doc["kb_id"]
        )
        is_owner = doc["user_id"] == current_user.user_id

        if not (is_owner or is_super_admin or is_kb_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this document",
            )

        # Delete vectors from Qdrant first
        delete_documents_by_doc_id(current_user.kb_name, doc_id)

        # Delete DB record
        await doc_repo.delete(doc_id)

    return ok(
        data={"doc_id": doc_id},
        message="Document deleted successfully",
    )
