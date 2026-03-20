"""Ingestion-layer constants.

Retrieval-mode and metadata-key constants have moved to
``docmind.core.metadata``.  Re-exported here for backwards compatibility.
"""

from __future__ import annotations

from docmind.core.metadata import (  # noqa: F401  (re-export)
    CHUNK_TYPE_CODE_BLOCK,
    CHUNK_TYPE_IMAGE,
    CHUNK_TYPE_TEXT,
    DEFAULT_RETRIEVAL_MODE,
    DEFAULT_STRICT_MODE,
    META_ALT_TEXT,
    META_CHUNK_TYPE,
    META_DOC_ID,
    META_FILE_PATH,
    META_IMAGE_URL,
    META_KB_NAME,
    META_ORIGINAL_CONTENT,
    META_RETRIEVAL_MODE,
    META_USER_ID,
    RETRIEVAL_MODE_CHUNK,
    RETRIEVAL_MODE_FULL_DOC,
    RETRIEVAL_MODES,
)
