"""
Simple structured logger — writes JSON lines to level-specific files.

File naming:  <LOG_DIR>/<YYYYMMDDHH>.<level>.log
    e.g.  logs/2026031119.debug.log

Each JSON line contains:
    - ts        : ISO-8601 timestamp with millisecond precision
    - topic     : caller-supplied context string
    - data      : arbitrary dict payload
    - caller    : {file, line, func} of the call site

Configuration (via .env / environment variables):
    LOG_DIR    — directory to write logs into (default: "logs")
    LOG_LEVEL  — minimum level: "debug" | "info" | "error" (default: "debug")
"""

from __future__ import annotations

import inspect
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from docmind.core.config import settings

# Level ordering — entries below the configured minimum are silently dropped
_LEVELS = {"debug": 0, "info": 1, "error": 2}


def _log_dir() -> Path:
    """Resolve log directory from settings (supports absolute and relative paths)."""
    d = Path(settings.log.dir)
    if not d.is_absolute():
        # Relative paths are anchored to the project root (two levels up from this file)
        d = Path(__file__).resolve().parent.parent.parent / d
    return d


def _write(level: str, topic: str, data: dict) -> None:
    """Build a JSON record and append it to the appropriate log file.

    Args:
        level: Log level string ("debug" | "info" | "error").
        topic: A short context tag, typically snake_case segments joined by
               underscores (e.g. "ingest_pdf_split").  This makes it trivial
               to grep for related entries later:
                   grep "ingest_pdf" logs/2026031119.debug.log
               No validation is enforced — the caller decides the convention.
        data:  Arbitrary JSON-serialisable dict carrying the structured payload.
    """
    # Drop entries below the configured minimum level
    if _LEVELS.get(level, 0) < _LEVELS.get(settings.log.level, 0):
        return

    log_dir = _log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    hour_prefix = now.strftime("%Y%m%d%H")            # e.g. "2026031119"
    filename = f"{hour_prefix}.{level}.log"            # e.g. "2026031119.debug.log"

    # Caller info (skip 2 frames: _write → debug/info/error → actual caller)
    frame = inspect.stack()[2]
    caller = {
        "file": os.path.basename(frame.filename),
        "line": frame.lineno,
        "func": frame.function,
    }

    record = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z",
        "topic": topic,
        "data": data,
        "caller": caller,
    }

    filepath = log_dir / filename
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as write_err:
        # Fallback to stderr so a logging failure never crashes the caller
        import sys as _sys
        _sys.stderr.write(
            f"[LOGGER FALLBACK] Failed to write log ({write_err}): "
            + json.dumps(record, ensure_ascii=False)
            + "\n"
        )


# ---------------------------------------------------------------------------
# Public API — three functions, three levels, dead simple
# ---------------------------------------------------------------------------

def debug(topic: str, data: dict) -> None:
    """Write a DEBUG-level log entry.

    Args:
        topic: Context tag for grep-friendly searching (snake_case recommended).
        data:  Structured payload as a dict.
    """
    _write("debug", topic, data)


def info(topic: str, data: dict) -> None:
    """Write an INFO-level log entry.

    Args:
        topic: Context tag for grep-friendly searching (snake_case recommended).
        data:  Structured payload as a dict.
    """
    _write("info", topic, data)


def error(topic: str, data: dict) -> None:
    """Write an ERROR-level log entry.

    Args:
        topic: Context tag for grep-friendly searching (snake_case recommended).
        data:  Structured payload as a dict.
    """
    _write("error", topic, data)
