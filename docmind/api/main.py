"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from docmind.core.config import settings
from docmind.api.response import ok, err, register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks and initialize resources before accepting requests."""
    missing = settings.validate()
    if missing:
        print(
            "[STARTUP ERROR] The following required environment variables are missing or invalid:\n"
            + "".join(f"  - {var}\n" for var in missing)
            + "Please set them in your .env file or environment and restart the application.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Initialize SQLite database (creates tables if they don't exist)
    from docmind.db.database import init_db
    await init_db()

    yield  # App is running


app = FastAPI(
    title="DocMind",
    description="RAG Knowledge Base powered by LangGraph",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Global Exception Handlers ──
register_exception_handlers(app)


# ── Routers ──

from docmind.api.routers import chat, ingest  # noqa: E402
from docmind.api.routers.auth import router as auth_router  # noqa: E402
from docmind.api.routers.kb import router as kb_router  # noqa: E402

app.include_router(auth_router)
app.include_router(kb_router)
app.include_router(ingest.router)
app.include_router(chat.router)


# ── Health Check ──


@app.get("/health")
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
