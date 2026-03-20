"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from docmind.api.lifespan import lifespan
from docmind.api.middleware.request_id import RequestIdMiddleware
from docmind.api.response import register_exception_handlers
from docmind.api.routers import auth, chat, chats, ingest, kb, health, search
from docmind.core.config import settings

app = FastAPI(
    title="DocMind",
    description="RAG Knowledge Base powered by LangGraph",
    version="0.1.0",
    lifespan=lifespan,
)

# ── Middleware ──
# NOTE: Middleware is applied in reverse order of registration.
# CORSMiddleware must be added last so it runs first (outermost layer).
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global Exception Handlers ──
register_exception_handlers(app)

# ── Routers ──
app.include_router(auth.router)
app.include_router(kb.router)
app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(chats.router)
app.include_router(search.router)
app.include_router(health.router)
