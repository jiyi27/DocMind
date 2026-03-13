"""API dependencies — injectable via FastAPI's Depends()."""

from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from docmind.auth.jwt import decode_token
from docmind.auth.schemas import UserContext
from docmind.core.config import settings

_bearer = HTTPBearer()


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
