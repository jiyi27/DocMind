"""API key authentication and usage tracking services."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

from docmind.auth.api_key import hash_api_key
from docmind.auth.schemas import UserContext
from docmind.core.time import utc_now_iso, utc_today_date
from docmind.db.database import get_db
from docmind.db.repositories import ApiKeyRepository


@dataclass(frozen=True)
class AuthenticatedApiKey:
    key_id: str
    daily_limit: int
    user_context: UserContext


async def authenticate_api_key(raw_api_key: str) -> AuthenticatedApiKey:
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

    return AuthenticatedApiKey(
        key_id=row["id"],
        daily_limit=int(row["daily_limit"]),
        user_context=UserContext(
            user_id=row["user_id"],
            username=row["username"],
            kb_id=row["kb_id"],
            kb_name=row["kb_name"],
            role=row["role"],
        ),
    )


async def enforce_api_key_daily_limit(api_key: AuthenticatedApiKey) -> None:
    async with get_db() as db:
        repo = ApiKeyRepository(db)
        usage_count = await repo.increment_daily_usage(api_key.key_id, utc_today_date())

    if usage_count > api_key.daily_limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="API key daily limit exceeded",
        )


async def record_api_key_usage(api_key: AuthenticatedApiKey) -> None:
    async with get_db() as db:
        repo = ApiKeyRepository(db)
        await repo.touch_last_used(api_key.key_id, utc_now_iso())


async def resolve_user_context_from_api_key(raw_api_key: str) -> UserContext:
    api_key = await authenticate_api_key(raw_api_key)
    await enforce_api_key_daily_limit(api_key)
    await record_api_key_usage(api_key)
    return api_key.user_context
