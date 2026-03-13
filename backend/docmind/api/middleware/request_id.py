"""Request ID middleware: assigns a unique ID to every request and logs it."""

from __future__ import annotations

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

import docmind.core.logger as logger
from docmind.core.logger import set_request_id


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
