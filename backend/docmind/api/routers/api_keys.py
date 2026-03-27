"""User API key management."""

from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, status

from docmind.api.dependencies import get_current_user
from docmind.api.response import ok
from docmind.auth.api_key import generate_api_key
from docmind.auth.schemas import UserContext
from docmind.db.database import get_db
from docmind.db.repositories import ApiKeyRepository

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    daily_limit: int = Field(default=1000, gt=0, le=1_000_000)


@router.get("", summary="List API Keys")
async def list_api_keys(
    current_user: UserContext = Depends(get_current_user),
):
    async with get_db() as db:
        repo = ApiKeyRepository(db)
        keys = await repo.list_by_user(current_user.user_id)
    return ok(keys)


@router.post("", summary="Create API Key")
async def create_api_key(
    body: ApiKeyCreateRequest,
    current_user: UserContext = Depends(get_current_user),
):
    raw_key, key_hash, key_prefix = generate_api_key()

    async with get_db() as db:
        repo = ApiKeyRepository(db)
        created = await repo.create(
            user_id=current_user.user_id,
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=body.name.strip(),
            daily_limit=body.daily_limit,
        )

    return ok(
        {
            **created,
            "raw_key": raw_key,
        },
        message="API key created successfully",
    )


@router.delete("/{key_id}", summary="Deactivate API Key")
async def delete_api_key(
    key_id: str,
    current_user: UserContext = Depends(get_current_user),
):
    async with get_db() as db:
        repo = ApiKeyRepository(db)
        existing = await repo.get_by_id_for_user(key_id, current_user.user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found",
            )

        deleted = await repo.deactivate(key_id, current_user.user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate API key",
            )

    return ok(message="API key deactivated successfully")
