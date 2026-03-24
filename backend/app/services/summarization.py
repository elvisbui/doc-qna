"""Conversation history summarization service.

When chat history exceeds a threshold, older messages are summarized into
a concise summary using the LLM, preserving key facts and context while
reducing token usage. Falls back to simple truncation on error.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.providers.base import LLMProvider

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = (
    "Summarize the following conversation in 2-3 concise sentences, preserving key facts and context:\n\n{transcript}"
)


def _format_transcript(messages: list[dict]) -> str:
    """Format a list of message dicts as a readable conversation transcript.

    Args:
        messages: List of dicts with ``role`` and ``content`` keys.

    Returns:
        A newline-separated string with each message formatted as
        ``"Role: content"``.
    """
    lines: list[str] = []
    for msg in messages:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


async def summarize_history(
    messages: list[dict],
    llm_provider: LLMProvider,
    max_recent: int = 6,
) -> tuple[str | None, list[dict]]:
    """Summarize older conversation messages and return recent ones.

    If the conversation is short enough (``<= max_recent`` messages), no
    summarization is performed and the messages are returned as-is.

    When summarization is needed, the older messages are formatted as a
    transcript and sent to the LLM for a 2-3 sentence summary. The summary
    and the most recent messages are returned.

    If the LLM call fails for any reason, falls back to simple truncation
    (returning ``None`` summary and the last ``max_recent`` messages).

    Args:
        messages: Full conversation history as a list of role/content dicts.
        llm_provider: An LLM provider satisfying the ``LLMProvider`` protocol.
        max_recent: Number of recent messages to keep unsummarized.

    Returns:
        A tuple of ``(summary_or_none, recent_messages)``.
    """
    if len(messages) <= max_recent:
        return None, messages

    old_messages = messages[:-max_recent]
    recent_messages = messages[-max_recent:]

    transcript = _format_transcript(old_messages)
    prompt = SUMMARIZE_PROMPT.format(transcript=transcript)

    try:
        summary = await llm_provider.generate(prompt, context="")
        return summary.strip(), recent_messages
    except Exception:
        logger.warning(
            "Summarization failed, falling back to truncation",
            exc_info=True,
        )
        return None, recent_messages
