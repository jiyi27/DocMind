"""Unified API response helpers and global exception handler registration.

Every endpoint — success or failure — returns the same JSON envelope::

    {"code": 0,  "message": "ok",            "data": {...}}   # success
    {"code": -1, "message": "<description>", "data": null}    # failure

HTTP status is always 200 so that clients only need to inspect ``code``.

Exception handler priority (highest → lowest)
---------------------------------------------
1. AppException          – known business errors; message is safe to expose
2. RequestValidationError – Pydantic / FastAPI request validation failure
3. Exception             – catch-all; logs full details, returns generic message
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from docmind.core.exceptions import AppException
from docmind.core import logger


# ── Response envelope ──────────────────────────────────────────────────────────

def ok(data: Any = None, message: str = "ok") -> JSONResponse:
    """Return a successful JSON response."""
    return JSONResponse(
        status_code=200,
        content={"code": 0, "message": message, "data": data},
    )


def err(message: str, data: Any = None) -> JSONResponse:
    """Return an error JSON response (code=-1)."""
    return JSONResponse(
        status_code=200,
        content={"code": -1, "message": message, "data": data},
    )


# ── Exception handler registration ────────────────────────────────────────────

def register_exception_handlers(app: FastAPI) -> None:
    """Attach all global exception handlers to *app*.

    Call this once during application startup, before any requests are served.
    """

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        """Handle known business exceptions.

        The ``message`` on AppException subclasses is intentionally user-facing,
        so it is safe to return directly to the client.
        """
        logger.warning("app_exception", {
            "method": request.method,
            "url": str(request.url),
            "error_type": type(exc).__name__,
            "message": exc.message,
        })
        return err(exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle Pydantic / FastAPI request validation errors (bad input from client)."""
        logger.warning("request_validation_error", {
            "method": request.method,
            "url": str(request.url),
            "errors": exc.errors(),
        })
        return err("Invalid request parameters. Please check your input and try again.")

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all handler — log full details, return a safe generic message.

        Never leaks internal error details or tracebacks to the client.
        """
        logger.error("unhandled_exception", {
            "method": request.method,
            "url": str(request.url),
            "error_type": type(exc).__name__,
            "error": str(exc),
        })
        return err("An unexpected error occurred. Please try again later.")
