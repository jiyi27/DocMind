"""
Pydantic schemas for authentication and user management.
"""

from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    kb_id: str  # UUID of the chosen knowledge base


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    kb_id: str
    kb_name: str
    role: str
    created_at: str


class UserContext(BaseModel):
    """Parsed JWT payload — injected into route handlers via Depends."""
    user_id: str
    username: str
    kb_id: str
    kb_name: str   # knowledge base slug, used to derive Qdrant collection name
    role: str
