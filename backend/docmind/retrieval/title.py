"""Async session title generation via LLM.

Called as a fire-and-forget background task after the first turn of a new
conversation. The generated title is written back to the chat_sessions table.
"""

from __future__ import annotations

from docmind.core import logger
from docmind.core.llm import get_llm
from docmind.db.database import get_db
from docmind.db.repositories import ChatSessionRepository

_TITLE_PROMPT = """\
Based on the following conversation, generate a concise title of 5-10 words that \
captures the main topic. Reply with only the title, no punctuation at the start or end, \
no quotes.

User: {user_input}
Assistant: {assistant_answer}

Title:"""


async def generate_session_title(
    session_id: str,
    user_input: str,
    assistant_answer: str,
) -> None:
    """Generate a short title for a chat session using the LLM and persist it.

    Designed to run as an asyncio background task (fire-and-forget).
    All exceptions are swallowed — a failed title generation must never
    affect the main chat response.
    """
    try:
        llm = get_llm()
        prompt = _TITLE_PROMPT.format(
            user_input=user_input[:300],
            assistant_answer=assistant_answer[:300],
        )
        response = await llm.ainvoke(prompt)
        title = response.content.strip()

        # Guard against empty or excessively long LLM output
        if not title:
            return
        title = title[:80]

        async with get_db() as db:
            repo = ChatSessionRepository(db)
            await repo.update_title(session_id, title)

        logger.info(
            "session_title_generated", {"session_id": session_id, "title": title}
        )

    except Exception as exc:  # noqa: BLE001
        logger.error(
            "session_title_generation_failed",
            {"session_id": session_id, "error": str(exc)},
        )
