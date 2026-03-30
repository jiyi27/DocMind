"""Prompt templates for the RAG chat pipeline."""

from __future__ import annotations

from langchain_core.prompts import ChatPromptTemplate

RAG_SYSTEM_PROMPT = """\
You are a helpful assistant. Use the following context to answer the user's question.
Include inline citations like [1], [2], etc. in your answer where relevant.
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
