"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from docmind.api.lifespan import lifespan
from docmind.api.middleware.request_id import RequestIdMiddleware
from docmind.api.response import register_exception_handlers
from docmind.api.routers import auth, chat, ingest, kb, health

app = FastAPI(
    title="DocMind",
    description="RAG Knowledge Base powered by LangGraph",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware ──
app.add_middleware(RequestIdMiddleware)

# ── Global Exception Handlers ──
register_exception_handlers(app)

# ── Routers ──
app.include_router(auth.router)
app.include_router(kb.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(health.router)
