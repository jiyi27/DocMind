"""FastAPI application entry point."""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from docmind.core.config import settings
from docmind.core import logger
from docmind.ingestion.loaders import UnsupportedFileTypeError, DocumentLoadError
from docmind.vectorstore.qdrant_store import VectorStoreError


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup checks before accepting requests."""
    missing = settings.validate()
    if missing:
        print(
            "[STARTUP ERROR] The following required environment variables are missing or invalid:\n"
            + "".join(f"  - {var}\n" for var in missing)
            + "Please set them in your .env file or environment and restart the application.",
            file=sys.stderr,
        )
        sys.exit(1)

    yield  # App is running


app = FastAPI(
    title="DocMind",
    description="RAG Knowledge Base powered by LangGraph",
    version="0.1.0",
    lifespan=lifespan,
)


# ── Global Exception Handlers ──


@app.exception_handler(UnsupportedFileTypeError)
async def unsupported_file_type_handler(request: Request, exc: UnsupportedFileTypeError):
    """Translate UnsupportedFileTypeError to HTTP 400."""
    return JSONResponse(
        status_code=400,
        content={"error": "unsupported_file_type", "detail": "The uploaded file type is not supported."},
    )


@app.exception_handler(DocumentLoadError)
async def document_load_error_handler(request: Request, exc: DocumentLoadError):
    """Translate DocumentLoadError to HTTP 422 (Unprocessable Entity)."""
    logger.error("document_load_error", {
        "method": request.method,
        "url": str(request.url),
        "error_type": type(exc).__name__,
        "error": str(exc),
    })
    return JSONResponse(
        status_code=422,
        content={"error": "document_load_error", "detail": "The document could not be processed. Please check the file and try again."},
    )


@app.exception_handler(VectorStoreError)
async def vector_store_error_handler(request: Request, exc: VectorStoreError):
    """Translate VectorStoreError to HTTP 503 (Service Unavailable)."""
    logger.error("vector_store_error", {
        "method": request.method,
        "url": str(request.url),
        "error_type": type(exc).__name__,
        "error": str(exc),
    })
    return JSONResponse(
        status_code=503,
        content={"error": "service_unavailable", "detail": "The knowledge base service is temporarily unavailable. Please try again later."},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Catch-all handler — log the error and return a safe 500 response.

    Never leaks Python tracebacks to the client.
    """
    logger.error("unhandled_exception", {
        "method": request.method,
        "url": str(request.url),
        "error_type": type(exc).__name__,
        "error": str(exc),
    })
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "detail": "An unexpected error occurred. Please try again later.",
        },
    )


# ── Routers ──

from docmind.api.routers import chat, ingest  # noqa: E402

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

    status_code = 200 if overall == "ok" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "checks": checks},
    )
