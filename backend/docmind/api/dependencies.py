"""API dependencies — injectable via FastAPI's Depends()."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from docmind.auth.api_key import hash_api_key
from docmind.auth.jwt import decode_token
from docmind.auth.schemas import UserContext
from docmind.core.config import settings
from docmind.core.time import utc_now_iso, utc_today_date
from docmind.db.database import get_db
from docmind.db.repositories import ApiKeyRepository

_bearer = HTTPBearer()
_api_key_bearer = HTTPBearer(auto_error=False)


async def resolve_user_from_api_key(raw_api_key: str) -> UserContext:
    """Resolve a user context from a raw API key string."""
    key_hash = hash_api_key(raw_api_key)
    async with get_db() as db:
        repo = ApiKeyRepository(db)
        row = await repo.get_by_hash_with_user(key_hash)
        if not row or not int(row.get("is_active", 0)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        usage_count = await repo.increment_daily_usage(row["id"], utc_today_date())
        if usage_count > int(row["daily_limit"]):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="API key daily limit exceeded",
            )

        await repo.touch_last_used(row["id"], utc_now_iso())

    return UserContext(
        user_id=row["user_id"],
        username=row["username"],
        kb_id=row["kb_id"],
        kb_name=row["kb_name"],
        role=row["role"],
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserContext:
    """
    Extract and validate the JWT from the Authorization: Bearer <token> header.
    Returns a UserContext with user identity and knowledge base info.
    """
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return UserContext(
        user_id=payload["sub"],
        username=payload["username"],
        kb_id=payload["kb_id"],
        kb_name=payload["kb_name"],
        role=payload["role"],
    )


async def require_super_admin(
    current_user: UserContext = Depends(get_current_user),
) -> UserContext:
    """
    Dependency that ensures the caller is both authenticated and listed in
    SUPER_ADMIN_USERNAMES.  Raises 403 Forbidden otherwise.
    """
    if current_user.username not in settings.admin.super_admin_usernames:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super-admin privileges required",
        )
    return current_user


async def get_user_from_api_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(_api_key_bearer),
) -> UserContext:
    """Resolve a user context from Authorization: Bearer <api_key>."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return await resolve_user_from_api_key(credentials.credentials)
