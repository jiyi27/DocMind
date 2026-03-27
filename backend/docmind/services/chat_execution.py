"""Reusable RAG chat execution services."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from docmind.retrieval.graph import rag_graph
from docmind.retrieval.nodes import retrieve, stream_generate


@dataclass(frozen=True)
class ChatCompletionResult:
    answer: str
    sources: list[str]


@dataclass(frozen=True)
class PreparedStreamResult:
    context: str
    sources: list[str]


def db_messages_to_langchain(rows: list[dict]) -> list[AnyMessage]:
    """Convert DB message rows to LangChain message objects."""
    result: list[AnyMessage] = []
    for row in rows:
        if row["role"] == "user":
            result.append(HumanMessage(content=row["content"]))
        else:
            result.append(AIMessage(content=row["content"]))
    return result


async def run_rag_completion(
    *,
    query: str,
    kb_name: str,
    history: list[AnyMessage],
) -> ChatCompletionResult:
    result = await asyncio.to_thread(
        rag_graph.invoke,
        {
            "query": query,
            "kb_name": kb_name,
            "messages": history,
        },
    )
    return ChatCompletionResult(
        answer=result.get("answer", ""),
        sources=result.get("sources", []),
    )


async def prepare_rag_stream(*, query: str, kb_name: str) -> PreparedStreamResult:
    context, sources = await asyncio.to_thread(retrieve, query, kb_name)
    return PreparedStreamResult(context=context, sources=sources)


async def stream_rag_completion(
    *,
    query: str,
    prepared: PreparedStreamResult,
    history: list[AnyMessage],
) -> AsyncGenerator[str, None]:
    async for text in stream_generate(
        query=query,
        context=prepared.context,
        sources=prepared.sources,
        messages=history,
    ):
        yield text
