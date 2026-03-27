"""Startup configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_MISSING: list[str] = []
_DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "data" / "docmind.db"
_VALID_LOG_LEVELS = {"debug", "info", "error"}


def _require_str(env_var: str) -> str:
    value = os.getenv(env_var, "").strip()
    if not value:
        _MISSING.append(env_var)
    return value


def _optional_int(env_var: str, default: int) -> int:
    raw = os.getenv(env_var, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        _MISSING.append(f"{env_var} (value {raw!r} is not a valid integer)")
        return default


def _optional_str(env_var: str, default: str) -> str:
    value = os.getenv(env_var, "").strip()
    return value or default


@dataclass(frozen=True)
class LogConfig:
    dir: str
    level: str


@dataclass(frozen=True)
class JWTConfig:
    secret_key: str
    algorithm: str
    expire_minutes: int


@dataclass(frozen=True)
class AdminConfig:
    super_admin_usernames: frozenset[str]


@dataclass(frozen=True)
class CORSConfig:
    allowed_origins: list[str]


@dataclass(frozen=True)
class DatabaseConfig:
    path: str


@dataclass(frozen=True)
class Settings:
    log: LogConfig
    jwt: JWTConfig
    admin: AdminConfig
    cors: CORSConfig
    database: DatabaseConfig

    def validate(self) -> list[str]:
        return list(_MISSING)


def _load_log_config() -> LogConfig:
    level = _optional_str("LOG_LEVEL", "INFO").strip()
    if level.lower() not in _VALID_LOG_LEVELS:
        _MISSING.append(
            f"LOG_LEVEL (value {level!r} is not valid; must be one of: "
            f"{sorted(_VALID_LOG_LEVELS)})"
        )
    return LogConfig(
        dir=_optional_str("LOG_DIR", "logs"),
        level=level,
    )


def _load_admin_config() -> AdminConfig:
    raw = _require_str("SUPER_ADMIN_USERNAMES")
    usernames = frozenset(name.strip() for name in raw.split(",") if name.strip())
    if not usernames:
        _MISSING.append("SUPER_ADMIN_USERNAMES (must contain at least one username)")
    return AdminConfig(super_admin_usernames=usernames)


def _build_settings() -> Settings:
    return Settings(
        log=_load_log_config(),
        jwt=JWTConfig(
            secret_key=_require_str("JWT_SECRET_KEY"),
            algorithm=_optional_str("JWT_ALGORITHM", "HS256"),
            expire_minutes=_optional_int("JWT_EXPIRE_MINUTES", 1440),
        ),
        admin=_load_admin_config(),
        cors=CORSConfig(
            allowed_origins=[
                origin.strip()
                for origin in _optional_str("CORS_ORIGINS", "*").split(",")
                if origin.strip()
            ],
        ),
        database=DatabaseConfig(
            path=os.getenv("DOCMIND_DB_PATH", "").strip() or str(_DEFAULT_DB_PATH)
        ),
    )


settings = _build_settings()
