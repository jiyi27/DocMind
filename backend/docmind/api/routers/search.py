"""Search router — pure vector retrieval endpoint without LLM generation."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from docmind.api.dependencies import get_current_user
from docmind.api.response import ok
from docmind.api.schemas import SearchRequest, SearchResponse, SearchResultItem
from docmind.auth.schemas import UserContext
from docmind.core import logger
from docmind.retrieval.nodes import retrieve_search_hits

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", summary="Vector Search")
async def search(
    request: SearchRequest,
    current_user: UserContext = Depends(get_current_user),
) -> JSONResponse:
    """Return the top-k most similar documents for a query without LLM generation.

    Runs vector similarity search against the specified knowledge base and returns
    ranked document results with the matched chunk content preview.
    """
    try:
        hits = await asyncio.to_thread(
            retrieve_search_hits,
            request.query,
            request.kb_name,
            request.top_k,
        )
    except Exception as exc:
        logger.error(
            "search_failed",
            {
                "query": request.query[:200],
                "kb_name": request.kb_name,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    results = [
        SearchResultItem(
            title=item.title,
            url=item.url,
            sourceLabel=item.source_label,
            score=round(item.score, 4),
            matchedContent=item.matched_content,
            matchedChunkType=item.matched_chunk_type,
            retrievalMode=item.retrieval_mode,
        )
        for item in hits
    ]

    return ok(SearchResponse(results=results).model_dump(by_alias=True))
