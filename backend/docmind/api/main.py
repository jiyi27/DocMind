"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import sys
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from docmind.core.config import settings
from docmind.core.logger import set_request_id
import docmind.core.logger as logger
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


# ── Request ID Middleware ──

class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a unique request ID and log incoming request parameters.

    On every request this middleware:
      1. Reads (or generates) a request ID and binds it to the async context.
      2. Logs method, path, query params, and JSON body (when applicable).
         multipart/form-data bodies are intentionally skipped — reading the
         stream here would corrupt file uploads; form fields are logged by
         name only via query-string representation.
      3. Echoes the request ID back in the ``X-Request-Id`` response header.
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
        set_request_id(request_id)

        await self._log_request(request)

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response

    async def _log_request(self, request: Request) -> None:
        content_type = request.headers.get("content-type", "")

        data: dict = {
            "method": request.method,
            "path": request.url.path,
            "query": dict(request.query_params),
        }

        if "application/json" in content_type:
            # Read body bytes, then re-inject so the route handler still sees them
            body_bytes = await request.body()
            try:
                import json as _json
                data["body"] = _json.loads(body_bytes)
            except Exception:
                data["body"] = body_bytes.decode(errors="replace")
        elif "multipart/form-data" in content_type:
            # Cannot consume the stream — log form field names from Content-Disposition
            # is unreliable at this stage; just note that a file upload is in progress.
            data["body"] = "<multipart — not logged>"

        logger.info("http_request", data)


app.add_middleware(RequestIdMiddleware)


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
