"""API key generation and hashing helpers."""

from __future__ import annotations

import hashlib
import secrets

API_KEY_PREFIX = "dm_"


def hash_api_key(raw_key: str) -> str:
    """Return a deterministic SHA-256 hash for a raw API key."""
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    """Return (raw_key, key_hash, key_prefix)."""
    token = secrets.token_urlsafe(32)
    raw_key = f"{API_KEY_PREFIX}{token}"
    key_hash = hash_api_key(raw_key)
    key_prefix = raw_key[:12]
    return raw_key, key_hash, key_prefix
