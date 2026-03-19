"""
Knowledge Base CRUD router.

POST   /kb              — create a new knowledge base (auto-creates Qdrant collection)
GET    /kb              — list all knowledge bases
GET    /kb/{kb_id}      — get knowledge base detail + document count
DELETE /kb/{kb_id}      — delete knowledge base (drops Qdrant collection + all doc records)
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from docmind.api.dependencies import require_super_admin
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.core.embedding import EmbeddingParams
from docmind.core.embedding_options import list_embedding_options
from docmind.db.database import get_db
from docmind.db.repositories import DocumentRepository, KBRepository
from docmind.vectorstore.qdrant_store import create_kb_collection, delete_kb_collection

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


class EmbeddingOverride(BaseModel):
    provider: Literal["openai_compatible", "huggingface"] = "openai_compatible"
    model: str = ""
    base_url: str = ""
    api_key: str = ""


class KBCreate(BaseModel):
    name: str  # slug, e.g. "india" → collection "docmind_india"
    display_name: str
    description: str = ""
    embedding: EmbeddingOverride = Field(default_factory=EmbeddingOverride)


class KBUpdate(BaseModel):
    display_name: str
    description: str = ""


class KBEmbeddingConnectionUpdate(BaseModel):
    base_url: str = ""
    api_key: str = ""


class KBOut(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    created_at: str
    embedding_provider: str
    embedding_model: str
    vector_dimension: int


def _build_embedding_params(body: "EmbeddingOverride") -> EmbeddingParams:
    provider = body.provider.strip()
    model = body.model.strip()
    base_url = body.base_url.strip()
    api_key = body.api_key.strip()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="embedding.provider is required",
        )
    if not model:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="embedding.model is required",
        )
    if provider == "openai_compatible":
        if not base_url:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="embedding.base_url is required for openai_compatible",
            )
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="embedding.api_key is required for openai_compatible",
            )

    return EmbeddingParams(
        provider=provider,
        base_url=base_url,
        api_key=api_key,
        model=model,
    )


def _serialize_kb(kb: dict) -> dict:
    """Hide sensitive values and expose frontend-friendly embedding metadata."""
    return {
        k: v for k, v in kb.items() if k != "embedding_api_key"
    } | {
        "embedding_api_key_configured": bool(kb.get("embedding_api_key")),
        "embedding_base_url_source": (
            "custom" if kb.get("embedding_base_url") else "default"
        ),
        "embedding_api_key_source": (
            "custom" if kb.get("embedding_api_key") else "default"
        ),
    }


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

    emb_params = _build_embedding_params(body.embedding)

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
        vector_dim = await create_kb_collection(body.name, emb_params)

        kb = await repo.create(
            name=body.name,
            display_name=body.display_name,
            description=body.description,
            embedding_provider=emb_params.provider,
            embedding_model=emb_params.model,
            embedding_base_url=emb_params.base_url,
            embedding_api_key=emb_params.api_key,
            vector_dimension=vector_dim,
        )

    # Don't expose api_key in response
    return ok(data=_serialize_kb(kb), message="Knowledge base created")


# ---------------------------------------------------------------------------
# GET /kb/embedding-options
# ---------------------------------------------------------------------------


@router.get("/embedding-options", summary="List Embedding Options")
async def get_embedding_options():
    """Return frontend-safe embedding provider options for KB creation."""
    return ok(data=list_embedding_options())


# ---------------------------------------------------------------------------
# GET /kb
# ---------------------------------------------------------------------------


@router.get("", summary="List Knowledge Bases")
async def list_knowledge_bases():
    """Return a list of all registered knowledge bases and their basic info."""
    async with get_db() as db:
        repo = KBRepository(db)
        kbs = await repo.list_all()
    # Don't expose api_key
    safe_kbs = [_serialize_kb(kb) for kb in kbs]
    return ok(data=safe_kbs)


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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        docs = await doc_repo.list_by_kb(kb_id)
        total_points = await doc_repo.sum_chunk_count_by_kb(kb_id)

    safe_kb = _serialize_kb(kb)
    return ok(data={**safe_kb, "document_count": len(docs), "total_points": total_points})


# ---------------------------------------------------------------------------
# PATCH /kb/{kb_id}
# ---------------------------------------------------------------------------


@router.patch("/{kb_id}", summary="Update Knowledge Base")
async def update_knowledge_base(
    kb_id: str,
    body: KBUpdate,
    _: UserContext = Depends(require_super_admin),
):
    """Update editable KB metadata without changing vector identity."""
    async with get_db() as db:
        repo = KBRepository(db)
        kb = await repo.get_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        updated = await repo.update_metadata(
            kb_id=kb_id,
            display_name=body.display_name,
            description=body.description,
        )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )
    return ok(data=_serialize_kb(updated), message="Knowledge base updated")


# ---------------------------------------------------------------------------
# PATCH /kb/{kb_id}/embedding-connection
# ---------------------------------------------------------------------------


@router.patch(
    "/{kb_id}/embedding-connection",
    summary="Update Knowledge Base Embedding Connection",
)
async def update_knowledge_base_embedding_connection(
    kb_id: str,
    body: KBEmbeddingConnectionUpdate,
    _: UserContext = Depends(require_super_admin),
):
    """Update only connection fields for the KB's existing embedding model."""
    async with get_db() as db:
        repo = KBRepository(db)
        kb = await repo.get_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        updated = await repo.update_embedding_connection(
            kb_id=kb_id,
            embedding_base_url=body.base_url.strip(),
            embedding_api_key=body.api_key.strip(),
        )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
        )
    return ok(data=_serialize_kb(updated), message="Embedding connection updated")


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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        # Delete all document records for this KB
        deleted_docs = await doc_repo.delete_by_kb(kb_id)

        # Drop Qdrant collection
        await delete_kb_collection(kb["name"])

        # Delete KB record
        await kb_repo.delete(kb_id)

    return ok(
        data={"kb_id": kb_id, "documents_removed": deleted_docs},
        message="Knowledge base deleted",
    )
