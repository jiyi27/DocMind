from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docmind.core.logger import _exception_chain, _serialize_traceback


def _build_exception_chain() -> RuntimeError:
    try:
        raise ValueError("root problem")
    except ValueError as inner:
        try:
            raise RuntimeError("wrapped once") from inner
        except RuntimeError as outer:
            return outer


def test_serialize_traceback_includes_frame_metadata() -> None:
    exc = _build_exception_chain()

    payload = _serialize_traceback(exc)

    assert payload["error_type"] == "RuntimeError"
    assert payload["error"] == "wrapped once"
    assert payload["origin"]["func"] == "_build_exception_chain"
    assert payload["trigger"]["func"] == "_build_exception_chain"
    assert payload["call_chain"]
    assert "RuntimeError: wrapped once" in payload["traceback"]


def test_exception_chain_reaches_root_cause() -> None:
    exc = _build_exception_chain()

    chain = _exception_chain(exc)

    assert [item["error_type"] for item in chain] == ["RuntimeError", "ValueError"]
    assert chain[-1]["error"] == "root problem"
