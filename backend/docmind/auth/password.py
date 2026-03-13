"""
Password hashing and verification using pwdlib with Argon2 backend.
"""

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_pwd_hash = PasswordHash([Argon2Hasher()])


def hash_password(plain: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return _pwd_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against an Argon2id hash."""
    return _pwd_hash.verify(plain, hashed)
