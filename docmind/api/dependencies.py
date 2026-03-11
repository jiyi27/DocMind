"""API dependencies — injectable via FastAPI's Depends().

Currently minimal. Future additions:
- get_current_user() for JWT/OAuth auth
- get_db_session() for relational DB access
- rate_limiter() for per-user throttling
"""

from __future__ import annotations


async def get_current_user():
    """Placeholder for future authentication.

    When auth is implemented, this will:
    1. Extract JWT from Authorization header
    2. Validate and decode the token
    3. Return the user object

    For now, returns a default anonymous user dict.
    """
    return {"user_id": "anonymous", "role": "user"}
