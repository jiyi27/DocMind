"""Health check router."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from docmind.core.config import settings
from docmind.api.response import ok, err

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check that verifies external dependencies."""
    checks: dict[str, str] = {}

    # Check Qdrant connectivity (run in thread to avoid blocking the event loop)
    try:
        from docmind.vectorstore.qdrant_store import get_vector_store
        await asyncio.to_thread(get_vector_store)
        checks["qdrant"] = "ok"
    except Exception as exc:
        checks["qdrant"] = f"error: {type(exc).__name__}"

    # Check LLM API Key presence
    if settings.llm.api_key:
        checks["llm_api_key"] = "configured"
    else:
        checks["llm_api_key"] = "missing"

    overall = "ok" if all(v in ("ok", "configured") for v in checks.values()) else "degraded"

    if overall == "ok":
        return ok({"status": overall, "checks": checks})
    return err("One or more dependencies are unavailable.", data={"status": overall, "checks": checks})
