"""
Knowledge Base CRUD router.

POST   /kb              — create a new knowledge base (auto-creates Qdrant collection)
GET    /kb              — list all knowledge bases
GET    /kb/{kb_id}      — get knowledge base detail + document count
DELETE /kb/{kb_id}      — delete knowledge base (drops Qdrant collection + all doc records)
POST   /kb/{kb_id}/sync/preview — preview manual Confluence sync impact
POST   /kb/{kb_id}/sync — trigger manual Confluence sync
GET    /kb/{kb_id}/sync/jobs — list sync job history
GET    /kb/{kb_id}/sync/jobs/{job_id}/records — list sync record details
"""

import asyncio
import threading
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from docmind.api.dependencies import require_super_admin
from docmind.api.response import ok
from docmind.auth.schemas import UserContext
from docmind.core.exceptions import ConfigError
from docmind.core.runtime_settings import get_runtime_settings_statuses
from docmind.core.embedding import EmbeddingParams
from docmind.core.embedding_options import list_embedding_options
from docmind.db.database import create_async_connection, get_db
from docmind.db.repositories import (
    DocumentRepository,
    KBRepository,
    SyncJobRepository,
    SyncRecordRepository,
)
from docmind.services.system_settings import (
    get_confluence_runtime_settings,
    get_runtime_settings,
)
from docmind.vectorstore.qdrant_store import create_kb_collection, delete_kb_collection

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


class EmbeddingOverride(BaseModel):
    provider: Literal["openai_compatible", "huggingface"] = "openai_compatible"
    model: str = ""
    base_url: str = ""
    api_key: str = ""


class ConfluenceSettings(BaseModel):
    root_page_id: str = ""
    sync_enabled: bool = False
    sync_interval_minutes: int = 5
    retrieval_mode: Literal["chunk", "full_doc"] = "chunk"


class ConfluenceSettingsPatch(BaseModel):
    root_page_id: str | None = None
    root_page_title: str | None = None
    sync_enabled: bool | None = None
    sync_interval_minutes: int | None = None
    retrieval_mode: Literal["chunk", "full_doc"] | None = None


class ConfluenceResolveRequest(BaseModel):
    url: str


class KBCreate(BaseModel):
    name: str  # slug, e.g. "india" → collection "docmind_india"
    display_name: str
    description: str = ""
    embedding: EmbeddingOverride = Field(default_factory=EmbeddingOverride)
    confluence: ConfluenceSettings | None = None


class KBUpdate(BaseModel):
    display_name: str
    description: str = ""
    confluence: ConfluenceSettingsPatch | None = None


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
    runtime = get_runtime_settings()
    confluence_status = get_runtime_settings_statuses(runtime)["confluence"]
    return {k: v for k, v in kb.items() if k != "embedding_api_key"} | {
        "embedding_api_key_configured": bool(kb.get("embedding_api_key")),
        "embedding_base_url_source": (
            "custom" if kb.get("embedding_base_url") else "default"
        ),
        "embedding_api_key_source": (
            "custom" if kb.get("embedding_api_key") else "default"
        ),
        "confluence_capability_enabled": bool(confluence_status["configured"]),
        "confluence_capability_message": str(confluence_status["message"]),
        "confluence_capability_missing_fields": list(
            confluence_status["missing_fields"]
        ),
    }


def _merge_confluence_settings(
    kb: dict,
    patch: "ConfluenceSettingsPatch",
) -> dict[str, str | bool | int]:
    return {
        "root_page_id": (
            patch.root_page_id
            if patch.root_page_id is not None
            else kb.get("confluence_root_page_id", "")
        ),
        "root_page_title": (
            patch.root_page_title
            if patch.root_page_title is not None
            else kb.get("confluence_root_page_title", "")
        ),
        "sync_enabled": (
            patch.sync_enabled
            if patch.sync_enabled is not None
            else bool(kb.get("confluence_sync_enabled"))
        ),
        "sync_interval_minutes": (
            patch.sync_interval_minutes
            if patch.sync_interval_minutes is not None
            else int(kb.get("confluence_sync_interval_minutes") or 5)
        ),
        "retrieval_mode": (
            patch.retrieval_mode
            if patch.retrieval_mode is not None
            else kb.get("confluence_retrieval_mode", "chunk")
        ),
    }


def _validate_confluence_settings(
    settings_payload: "ConfluenceSettings | dict[str, str | bool | int]",
) -> None:
    sync_interval_minutes = int(settings_payload["sync_interval_minutes"])
    if sync_interval_minutes < 5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="confluence.sync_interval_minutes must be at least 5",
        )

    if (
        bool(settings_payload["sync_enabled"])
        and not get_runtime_settings().confluence.enabled
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Confluence system settings are incomplete. Configure both "
                "Confluence Base URL and PAT in System Settings before enabling auto sync."
            ),
        )


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
    if body.confluence:
        _validate_confluence_settings(body.confluence.model_dump())

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
    kb_dict = dict(kb)

    # Apply optional Confluence settings at creation time
    if body.confluence:
        async with get_db() as db:
            repo = KBRepository(db)
            kb_dict = (
                await repo.update_confluence_settings(
                    kb_id=kb_dict["id"],
                    root_page_id=body.confluence.root_page_id,
                    root_page_title=body.confluence.root_page_title or "",
                    sync_enabled=body.confluence.sync_enabled,
                    sync_interval_minutes=body.confluence.sync_interval_minutes,
                    retrieval_mode=body.confluence.retrieval_mode,
                )
                or kb_dict
            )

    return ok(data=_serialize_kb(kb_dict), message="Knowledge base created")


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
    return ok(
        data={**safe_kb, "document_count": len(docs), "total_points": total_points}
    )


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

        # Apply optional Confluence settings
        if body.confluence:
            merged = _merge_confluence_settings(kb, body.confluence)
            _validate_confluence_settings(merged)
            updated = (
                await repo.update_confluence_settings(
                    kb_id=kb_id,
                    root_page_id=str(merged["root_page_id"]),
                    root_page_title=str(merged["root_page_title"]),
                    sync_enabled=bool(merged["sync_enabled"]),
                    sync_interval_minutes=int(merged["sync_interval_minutes"]),
                    retrieval_mode=str(merged["retrieval_mode"]),
                )
                or updated
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


# ---------------------------------------------------------------------------
# POST /kb/{kb_id}/sync — trigger manual Confluence sync
# ---------------------------------------------------------------------------


def _run_sync_in_thread(kb_id: str, job_id: str) -> None:
    """Execute Confluence sync in a background thread with its own event loop and DB connection."""
    from docmind.integrations.confluence.service import execute_sync

    async def _run() -> None:
        conn = await create_async_connection()
        try:
            await execute_sync(conn, kb_id, job_id)
        finally:
            await conn.close()

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


@router.post(
    "/{kb_id}/sync/preview",
    summary="Preview Confluence Sync Impact",
)
async def preview_confluence_sync(
    kb_id: str,
    _: UserContext = Depends(require_super_admin),
):
    """Scan the Confluence tree and return the expected sync impact."""
    if not get_runtime_settings().confluence.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confluence integration is not configured",
        )

    from docmind.integrations.confluence.client import ConfluenceTraversalError
    from docmind.integrations.confluence.service import plan_sync

    async with get_db() as db:
        kb_repo = KBRepository(db)
        kb = await kb_repo.get_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        if not kb.get("confluence_root_page_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Confluence root page configured for this KB",
            )

        job_repo = SyncJobRepository(db)
        active_job = await job_repo.get_active_by_kb(kb_id)
        if active_job:
            return ok(
                data={
                    "job_in_progress": True,
                    "active_job_id": active_job["id"],
                    "status": active_job["status"],
                },
                message="A Confluence sync job is already in progress",
            )

        try:
            _, _, summary = await plan_sync(db, kb_id)
        except ConfluenceTraversalError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=exc.message,
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to reach Confluence: {exc}",
            ) from exc

        if summary is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Confluence root page configured for this KB",
            )

    return ok(
        data={"job_in_progress": False, **summary.model_dump()},
        message="Confluence sync preview ready",
    )


@router.post(
    "/{kb_id}/sync",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Confluence Sync",
)
async def trigger_confluence_sync(
    kb_id: str,
    _: UserContext = Depends(require_super_admin),
):
    """Create a manual sync job and start processing in the background."""
    if not get_runtime_settings().confluence.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confluence integration is not configured",
        )

    async with get_db() as db:
        kb_repo = KBRepository(db)
        kb = await kb_repo.get_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        if not kb.get("confluence_root_page_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No Confluence root page configured for this KB",
            )

        job_repo = SyncJobRepository(db)
        active_job = await job_repo.get_active_by_kb(kb_id)
        if active_job:
            return ok(
                data={"job_id": active_job["id"], "status": active_job["status"]},
                message="A Confluence sync job is already in progress",
            )

        job = await job_repo.create(kb_id=kb_id, trigger_type="manual")

    # Run sync in a background thread so the API can respond immediately
    thread = threading.Thread(
        target=_run_sync_in_thread,
        args=(kb_id, job["id"]),
        name=f"confluence-sync-{kb_id[:8]}",
        daemon=True,
    )
    thread.start()

    return ok(
        data={"job_id": job["id"], "status": "pending"},
        message="Confluence sync started",
    )


# ---------------------------------------------------------------------------
# GET /kb/{kb_id}/sync/jobs — list sync job history
# ---------------------------------------------------------------------------


@router.get("/{kb_id}/sync/jobs", summary="List Sync Jobs")
async def list_sync_jobs(
    kb_id: str,
    limit: int = 20,
):
    """Return sync job history for a KB, ordered by created_at DESC."""
    async with get_db() as db:
        kb_repo = KBRepository(db)
        kb = await kb_repo.get_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

        job_repo = SyncJobRepository(db)
        jobs = await job_repo.list_by_kb(kb_id, limit=limit)

    return ok(data={"total": len(jobs), "jobs": jobs})


# ---------------------------------------------------------------------------
# GET /kb/{kb_id}/sync/jobs/{job_id}/records — list sync record details
# ---------------------------------------------------------------------------


@router.get("/{kb_id}/sync/jobs/{job_id}/records", summary="List Sync Records")
async def list_sync_records(
    kb_id: str,
    job_id: str,
):
    """Return all document-level sync records for a specific sync job."""
    async with get_db() as db:
        job_repo = SyncJobRepository(db)
        job = await job_repo.get_by_id(job_id)
        if not job or job["kb_id"] != kb_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Sync job not found"
            )

        record_repo = SyncRecordRepository(db)
        records = await record_repo.list_by_job(job_id)

    return ok(data={"total": len(records), "records": records})


# ---------------------------------------------------------------------------
# POST /kb/{kb_id}/confluence/resolve-page — resolve a Confluence URL to page metadata
# ---------------------------------------------------------------------------


@router.post(
    "/{kb_id}/confluence/resolve-page",
    summary="Resolve Confluence Page URL",
)
async def resolve_confluence_page(
    kb_id: str,
    body: ConfluenceResolveRequest,
    _: UserContext = Depends(require_super_admin),
):
    """Parse a Confluence page URL and return its page ID and title."""
    if not get_runtime_settings().confluence.enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confluence integration is not configured",
        )

    url = body.url.strip()
    if not url:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="url is required",
        )

    async with get_db() as db:
        repo = KBRepository(db)
        kb = await repo.get_by_id(kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge base not found"
            )

    from docmind.integrations.confluence.client import (
        ConfluenceClient,
        ConfluenceTraversalError,
    )

    try:
        confluence = get_confluence_runtime_settings()
    except ConfigError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    client = ConfluenceClient(base_url=confluence.base_url, pat=confluence.pat)
    try:
        page_id, title, source_url = await client.resolve_page_url(url)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except ConfluenceTraversalError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=exc.message)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to reach Confluence: {exc}",
        )
    finally:
        await client.close()

    return ok(
        data={"page_id": page_id, "title": title, "source_url": source_url},
        message="Page resolved successfully",
    )
