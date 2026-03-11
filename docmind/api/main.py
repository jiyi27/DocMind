"""FastAPI application entry point."""

from __future__ import annotations

from fastapi import FastAPI

from docmind.api.routers import chat, ingest

app = FastAPI(
    title="DocMind",
    description="RAG Knowledge Base powered by LangGraph",
    version="0.1.0",
)

app.include_router(ingest.router)
app.include_router(chat.router)


@app.get("/health")
async def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}

