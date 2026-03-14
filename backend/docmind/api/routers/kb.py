"""
Knowledge Base CRUD router.

POST   /kb              — create a new knowledge base (auto-creates Qdrant collection)
GET    /kb              — list all knowledge bases
GET    /kb/{kb_id}      — get knowledge base detail + document count
DELETE /kb/{kb_id}      — delete knowledge base (drops Qdrant collection + all doc records)
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from docmind.api.dependencies import require_super_admin
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.db.database import get_db
from docmind.db.repositories import KBRepository, DocumentRepository
from docmind.vectorstore.qdrant_store import create_kb_collection, delete_kb_collection

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


class KBCreate(BaseModel):
    name: str           # slug, e.g. "india" → collection "docmind_india"
    display_name: str
    description: str = ""


class KBOut(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    created_at: str


# ---------------------------------------------------------------------------
# POST /kb
# ---------------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED, summary="Create Knowledge Base")
async def create_knowledge_base(
    body: KBCreate,
    _: UserContext = Depends(require_super_admin),
):
    """Initialize a new knowledge base and its corresponding vector collection (Super-admin only)."""
    # Validate slug format
    if not body.name.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="name must be alphanumeric (underscores/hyphens allowed)",
        )

    async with get_db() as db:
        repo = KBRepository(db)

        # Check uniqueness
        existing = await repo.get_by_name(body.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Knowledge base '{body.name}' already exists",
            )

        # Create Qdrant collection first — if it fails, we don't write to DB
        await create_kb_collection(body.name)

        kb = await repo.create(
            name=body.name,
            display_name=body.display_name,
            description=body.description,
        )

    return ok(data=kb, message="Knowledge base created")


# ---------------------------------------------------------------------------
# GET /kb
# ---------------------------------------------------------------------------

@router.get("", summary="List Knowledge Bases")
async def list_knowledge_bases():
    """Return a list of all registered knowledge bases and their basic info."""
    async with get_db() as db:
        repo = KBRepository(db)
        kbs = await repo.list_all()
    return ok(data=kbs)


# ---------------------------------------------------------------------------
# GET /kb/{kb_id}
# ---------------------------------------------------------------------------

@router.get("/{kb_id}", summary="Get Knowledge Base Details")
async def get_knowledge_base(kb_id: str):
    """Retrieve detailed configuration and statistics (e.g., total documents and chunks) for a specific KB."""
    async with get_db() as db:
        kb_repo = KBRepository(db)
        doc_repo = DocumentRepository(db)

        kb = await kb_repo.get_by_id(kb_id)
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

        docs = await doc_repo.list_by_kb(kb_id)
        total_points = await doc_repo.sum_chunk_count_by_kb(kb_id)

    return ok(data={**kb, "document_count": len(docs), "total_points": total_points})


# ---------------------------------------------------------------------------
# DELETE /kb/{kb_id}
# ---------------------------------------------------------------------------

@router.delete("/{kb_id}", summary="Delete Knowledge Base")
async def delete_knowledge_base(
    kb_id: str,
    _: UserContext = Depends(require_super_admin),
):
    """Completely remove a KB, its document records, and its vector collection (Super-admin only)."""
    async with get_db() as db:
        kb_repo = KBRepository(db)
        doc_repo = DocumentRepository(db)

        kb = await kb_repo.get_by_id(kb_id)
        if not kb:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found")

        # Delete all document records for this KB
        deleted_docs = await doc_repo.delete_by_kb(kb_id)

        # Drop Qdrant collection
        await delete_kb_collection(kb["name"])

        # Delete KB record
        await kb_repo.delete(kb_id)

    return ok(data={"kb_id": kb_id, "documents_removed": deleted_docs}, message="Knowledge base deleted")
