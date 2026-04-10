"""Prompt templates for the RAG chat pipeline."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

# Legacy prompt: relies on the structured `citations` field returned alongside
# the response for clients that can render source lists natively.
# RAG_SYSTEM_PROMPT = """\
# You are a helpful assistant. Use the following context to answer the user's question.
# Include inline citations like [1], [2], etc. in your answer where relevant.
# Context:
# {context}
#
# Available citations:
# {citations}
# """

RAG_SYSTEM_PROMPT = """\
You are a helpful assistant. Use the following context to answer the user's question.

Rules:
1. Include inline citations like [1], [2], etc. in your answer where relevant.
2. At the end of your answer, add a "Sources:" section listing only the citations \
you actually referenced, copying them exactly from the available citations below.

Context:
{context}

Available citations:
{citations}
"""

rag_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", RAG_SYSTEM_PROMPT),
        ("placeholder", "{messages}"),
    ]
)
