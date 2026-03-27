"""Shared time helpers."""

from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso() -> str:
    """Return the current UTC time in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


def utc_today_date() -> str:
    """Return the current UTC date in YYYY-MM-DD format."""
    return datetime.now(timezone.utc).date().isoformat()
