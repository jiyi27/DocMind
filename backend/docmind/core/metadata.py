"""Shared metadata key and value constants for ingestion and retrieval.

Both layers read/write Qdrant document metadata using these keys.
Centralising them here makes the ingestion→retrieval contract explicit
and prevents silent mismatches from string-literal typos.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Retrieval mode
# ---------------------------------------------------------------------------

RETRIEVAL_MODE_CHUNK: Final = "chunk"
RETRIEVAL_MODE_FULL_DOC: Final = "full_doc"
RETRIEVAL_MODES: Final = (RETRIEVAL_MODE_CHUNK, RETRIEVAL_MODE_FULL_DOC)

DEFAULT_RETRIEVAL_MODE: Final = RETRIEVAL_MODE_CHUNK
DEFAULT_STRICT_MODE: Final = False

# ---------------------------------------------------------------------------
# Metadata keys
# ---------------------------------------------------------------------------

META_DOC_ID: Final = "doc_id"
META_USER_ID: Final = "user_id"
META_KB_NAME: Final = "kb_name"
META_FILE_PATH: Final = "file_path"
META_RETRIEVAL_MODE: Final = "retrieval_mode"
META_CHUNK_TYPE: Final = "chunk_type"
META_ORIGINAL_CONTENT: Final = "original_content"
META_IMAGE_URL: Final = "image_url"
META_ALT_TEXT: Final = "alt_text"
META_TITLE: Final = "title"
META_FILE_NAME: Final = "file_name"
META_SOURCE: Final = "source"
META_URL: Final = "url"

# ---------------------------------------------------------------------------
# chunk_type values
# ---------------------------------------------------------------------------

CHUNK_TYPE_TEXT: Final = "text"
CHUNK_TYPE_CODE_MIXED: Final = "code_mixed"
CHUNK_TYPE_IMAGE: Final = "image"
CHUNK_TYPE_FULL_DOC: Final = "full_doc"
