"""
Authentication router.

POST /auth/register  — register a new user (choose a knowledge base)
POST /auth/login     — login with username + password → JWT
"""

from fastapi import APIRouter, HTTPException, status

from docmind.api.response import ok
from docmind.auth.password import hash_password, verify_password
from docmind.auth.jwt import create_access_token
from docmind.auth.schemas import UserCreate, LoginRequest, TokenResponse, UserOut
from docmind.core.config import settings
from docmind.db.database import get_db
from docmind.db.repositories import UserRepository, KBRepository

router = APIRouter(prefix="/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate):
    async with get_db() as db:
        kb_repo = KBRepository(db)
        user_repo = UserRepository(db)

        # Validate knowledge base exists
        kb = await kb_repo.get_by_id(body.kb_id)
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Knowledge base '{body.kb_id}' not found",
            )

        # Check username uniqueness
        if await user_repo.get_by_username(body.username):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already taken",
            )

        hashed = hash_password(body.password)
        user = await user_repo.create(
            username=body.username,
            hashed_password=hashed,
            kb_id=body.kb_id,
        )

    return ok(
        data=UserOut(
            id=user["id"],
            username=user["username"],
            kb_id=user["kb_id"],
            kb_name=kb["name"],
            role=user["role"],
            created_at=user["created_at"],
        ).model_dump(),
        message="User registered successfully",
    )


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post("/login")
async def login(body: LoginRequest):
    async with get_db() as db:
        user_repo = UserRepository(db)
        kb_repo = KBRepository(db)

        user = await user_repo.get_by_username(body.username)
        if not user or not verify_password(body.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        kb = await kb_repo.get_by_id(user["kb_id"])
        if not kb:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User's knowledge base not found",
            )

    token = create_access_token({
        "sub": user["id"],
        "username": user["username"],
        "kb_id": user["kb_id"],
        "kb_name": kb["name"],
        "role": user["role"],
    })

    is_super_admin = user["username"] in settings.admin.super_admin_usernames

    return ok(
        data=TokenResponse(
            access_token=token,
            is_super_admin=is_super_admin,
            kb_id=user["kb_id"],
            role=user["role"],
            username=user["username"]
        ).model_dump(),
        message="Login successful",
    )
