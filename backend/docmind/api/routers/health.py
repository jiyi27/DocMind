"""Health check router."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter

from docmind.api.response import ok, err
from docmind.services.system_settings import (
    get_llm_runtime_settings,
    get_qdrant_runtime_settings,
)

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health Check")
async def health_check():
    """Verify system status and connectivity of external dependencies (Qdrant, LLM API, etc.)."""
    checks: dict[str, str] = {}

    # Check Qdrant connectivity (run in thread to avoid blocking the event loop)
    try:
        from docmind.vectorstore.qdrant_store import check_qdrant_connection

        get_qdrant_runtime_settings()
        await asyncio.to_thread(check_qdrant_connection)
        checks["qdrant"] = "ok"
    except Exception as exc:
        checks["qdrant"] = f"error: {type(exc).__name__}"

    try:
        get_llm_runtime_settings()
        checks["llm"] = "configured"
    except Exception:
        checks["llm"] = "missing"

    overall = (
        "ok" if all(v in ("ok", "configured") for v in checks.values()) else "degraded"
    )

    if overall == "ok":
        return ok({"status": overall, "checks": checks})
    return err(
        "One or more dependencies are unavailable.",
        data={"status": overall, "checks": checks},
    )
