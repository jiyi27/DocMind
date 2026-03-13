"""
Simple structured logger — writes JSON lines to level-specific files.

File naming:  <LOG_DIR>/<YYYYMMDDHH>.<level>.log
    e.g.  logs/2026031119.debug.log

Each JSON line contains:
    - ts        : ISO-8601 timestamp with millisecond precision
    - topic     : caller-supplied context string
    - data      : arbitrary dict payload
    - caller    : {file, line, func} of the log call site

When an exception is active (inside an except block), ``data`` is automatically
enriched with three extra keys:
    - origin     : {file, line, func} — outermost traceback frame (entry point)
    - trigger    : {file, line, func, code} — innermost frame (raise site)
    - call_chain : list of "file:line func" strings, outermost → innermost

Configuration (via .env / environment variables):
    LOG_DIR    — directory to write logs into (default: "logs")
    LOG_LEVEL  — minimum level: "debug" | "info" | "error" (default: "debug")
"""

from __future__ import annotations

import inspect
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from docmind.core.config import settings

# Level ordering — entries below the configured minimum are silently dropped
_LEVELS = {"debug": 0, "info": 1, "warning": 2, "error": 3}


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

    now = datetime.now()  # local time
    hour_prefix = now.strftime("%Y%m%d%H")            # e.g. "2026031219"
    filename = f"{hour_prefix}.{level}.log"            # e.g. "2026031219.debug.log"

    # Caller info (skip 2 frames: _write → debug/info/error → actual caller)
    frame = inspect.stack()[2]
    caller = {
        "file": os.path.basename(frame.filename),
        "line": frame.lineno,
        "func": frame.function,
    }

    record: dict = {
        "ts": now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}+08:00",
        "topic": topic,
        "data": data,
        "caller": caller,
    }

    # If there is an active exception, enrich the record with traceback details.
    exc_type, exc_value, exc_tb = sys.exc_info()
    if exc_value is not None:
        frames = traceback.extract_tb(exc_tb)
        if frames:
            # origin — where the exception propagated through our handler (outermost tb frame)
            origin_frame = frames[0]
            record["data"] = dict(data)  # shallow copy so we don't mutate the caller's dict
            record["data"]["origin"] = {
                "file": os.path.basename(origin_frame.filename),
                "line": origin_frame.lineno,
                "func": origin_frame.name,
            }
            # trigger — the innermost frame where the exception was actually raised
            trigger_frame = frames[-1]
            record["data"]["trigger"] = {
                "file": os.path.basename(trigger_frame.filename),
                "line": trigger_frame.lineno,
                "func": trigger_frame.name,
                "code": trigger_frame.line,
            }
            # call_chain — every frame in the traceback, outermost → innermost
            record["data"]["call_chain"] = [
                f"{os.path.basename(f.filename)}:{f.lineno} {f.name}"
                for f in frames
            ]

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


def warning(topic: str, data: dict) -> None:
    """Write a WARNING-level log entry.

    Use for expected-but-notable events: business exceptions, bad client input,
    suspicious activity — anything that is not a server bug but warrants attention.

    Args:
        topic: Context tag for grep-friendly searching (snake_case recommended).
        data:  Structured payload as a dict.
    """
    _write("warning", topic, data)


def error(topic: str, data: dict) -> None:
    """Write an ERROR-level log entry.

    Args:
        topic: Context tag for grep-friendly searching (snake_case recommended).
        data:  Structured payload as a dict.
    """
    _write("error", topic, data)
