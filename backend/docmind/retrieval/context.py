"""Structured intermediate representation for retrieved content.

A ContextItem captures one retrieved chunk together with its type and
all metadata needed by the generate node to compose LLM message content.
Using a typed structure instead of a flat string lets the generate node
handle text, code, image, and full-doc chunks differently without
requiring shared mutable state or ad-hoc string parsing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


@dataclass
class Citation:
    """Structured citation metadata returned to API clients."""

    index: int
    title: str
    url: str
    source_label: str

    def to_dict(self) -> dict[str, int | str]:
        payload = asdict(self)
        payload["sourceLabel"] = payload.pop("source_label")
        return payload


@dataclass
class ContextItem:
    """One resolved retrieval result, ready for LLM message assembly.

    Attributes
    ----------
    index:
        1-based citation index used in ``[1]``, ``[2]`` references.
    chunk_type:
        Content category.  Determines how the generate node incorporates
        this item into the LLM message:
        - ``"text"``     — plain prose; included in the text context block.
        - ``"code"``     — original source code (restored from metadata);
                           included in the text context block.
        - ``"image"``    — caption/summary used for semantic search;
                           ``image_url`` carries the actual image reference.
        - ``"full_doc"`` — entire document text loaded from disk.
    content:
        The text to include in the context string.  For image chunks this
        is the LLM-generated caption stored at index time, not the image
        itself.
    image_url:
        Raw image URL or local path.  Only set for ``chunk_type == "image"``.
        Reserved for Step 2 (multimodal message assembly).
    title:
        Human-readable document title for the citation line.
    url:
        External URL of the source document, if available.
    source_label:
        Pre-formatted citation string, e.g. ``"[1] [My Doc](https://...)"``
        or ``"[1] My Doc"``.  Built once during retrieval so the generate
        node does not need to reconstruct it.
    """

    index: int
    chunk_type: Literal["text", "code", "image", "full_doc"]
    content: str
    image_url: str | None = None
    title: str = ""
    url: str = ""
    source_label: str = field(default="")


@dataclass
class SearchHit:
    """One document-level search result derived from a matched chunk."""

    title: str
    url: str
    source_label: str
    score: float
    matched_content: str
    matched_chunk_type: str
    retrieval_mode: str
