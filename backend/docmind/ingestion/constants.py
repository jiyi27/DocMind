"""Shared ingestion defaults and enums."""

from __future__ import annotations

from typing import Final

RETRIEVAL_MODE_CHUNK: Final = "chunk"
RETRIEVAL_MODE_FULL_DOC: Final = "full_doc"
RETRIEVAL_MODES: Final = (RETRIEVAL_MODE_CHUNK, RETRIEVAL_MODE_FULL_DOC)

DEFAULT_RETRIEVAL_MODE: Final = RETRIEVAL_MODE_CHUNK
DEFAULT_STRICT_MODE: Final = True
