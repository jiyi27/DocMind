"""
JWT token creation and verification using PyJWT.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from docmind.core.config import settings


def create_access_token(payload: dict[str, Any]) -> str:
    """
    Create a signed JWT access token.

    The caller should pass at minimum:
        {"sub": user_id, "username": ..., "kb_id": ..., "kb_name": ..., "role": ...}

    The `exp` claim is added automatically.
    """
    data = payload.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt.expire_minutes)
    data["exp"] = expire
    return jwt.encode(data, settings.jwt.secret_key, algorithm=settings.jwt.algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and verify a JWT token.

    Raises:
        jwt.ExpiredSignatureError  — token has expired
        jwt.InvalidTokenError      — token is invalid / tampered
    """
    return jwt.decode(token, settings.jwt.secret_key, algorithms=[settings.jwt.algorithm])
