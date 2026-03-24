"""Tests for conversation history summarization service."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.core.exceptions import ProviderError
from app.services.generation import generate_answer_stream
from app.services.summarization import _format_transcript, summarize_history

# ---------------------------------------------------------------------------
# Fake providers
# ---------------------------------------------------------------------------


class FakeLLMProvider:
    """Fake LLM that returns a canned summary via generate() and streams tokens."""

    def __init__(self, summary: str = "This is a summary of the conversation."):
        self._summary = summary

    async def generate(self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any) -> str:
        return self._summary

    async def generate_stream(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        yield "Hello "
        yield "world"


class FailingLLMProvider:
    """Fake LLM whose generate() raises an error (simulating summarization failure)."""

    async def generate(self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any) -> str:
        raise ProviderError(provider="fake", reason="LLM unavailable")

    async def generate_stream(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        yield "Hello "
        yield "world"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_messages(n: int) -> list[dict]:
    """Create n alternating user/assistant messages."""
    messages = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        messages.append({"role": role, "content": f"Message {i}"})
    return messages


def _test_settings(tmp_path) -> Settings:
    return Settings(
        UPLOAD_DIR=str(tmp_path / "uploads"),
        CHROMA_PERSIST_DIR=str(tmp_path / "chroma"),
        OPENAI_API_KEY="fake-key",
        EMBEDDING_PROVIDER="openai",
        LLM_PROVIDER="ollama",
        CORS_ORIGINS=["*"],
        LOG_LEVEL="WARNING",
    )


def _parse_sse_events(text: str) -> list[dict]:
    """Parse raw SSE text into a list of {event, data} dicts."""
    events = []
    current_event = "message"
    data_lines = []

    for line in text.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            data_lines.append(line[6:])
        elif line == "":
            if data_lines:
                events.append({"event": current_event, "data": "\n".join(data_lines)})
                data_lines = []
                current_event = "message"

    if data_lines:
        events.append({"event": current_event, "data": "\n".join(data_lines)})

    return events


# ---------------------------------------------------------------------------
# Tests — summarize_history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_short_history_returns_none_and_unchanged():
    """History with <= max_recent messages should return None summary."""
    messages = _make_messages(4)
    provider = FakeLLMProvider()

    summary, result = await summarize_history(messages, provider, max_recent=6)

    assert summary is None
    assert result == messages


@pytest.mark.asyncio
async def test_exact_threshold_returns_none():
    """History with exactly max_recent messages should not summarize."""
    messages = _make_messages(6)
    provider = FakeLLMProvider()

    summary, result = await summarize_history(messages, provider, max_recent=6)

    assert summary is None
    assert result == messages


@pytest.mark.asyncio
async def test_long_history_calls_llm_and_returns_summary():
    """History exceeding max_recent should call LLM and return summary + recent."""
    messages = _make_messages(10)
    expected_summary = "This is a summary of the conversation."
    provider = FakeLLMProvider(summary=expected_summary)

    summary, recent = await summarize_history(messages, provider, max_recent=6)

    assert summary == expected_summary
    assert len(recent) == 6
    assert recent == messages[-6:]


@pytest.mark.asyncio
async def test_llm_failure_falls_back_to_truncation():
    """When LLM fails, summarize_history should return None and recent messages."""
    messages = _make_messages(10)
    provider = FailingLLMProvider()

    summary, recent = await summarize_history(messages, provider, max_recent=6)

    assert summary is None
    assert len(recent) == 6
    assert recent == messages[-6:]


@pytest.mark.asyncio
async def test_format_transcript():
    """_format_transcript should produce a readable conversation string."""
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    result = _format_transcript(messages)
    assert result == "User: Hello\nAssistant: Hi there"


# ---------------------------------------------------------------------------
# Tests — SSE summary event in generate_answer_stream
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_summary_event_emitted_for_long_history(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """generate_answer_stream should emit a summary SSE event when history is summarized."""
    settings = _test_settings(tmp_path)
    history = _make_messages(10)

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        history=history,
        llm_provider=FakeLLMProvider(),
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    event_types = [e["event"] for e in events]
    assert "summary" in event_types, f"Expected summary event, got: {event_types}"

    summary_event = next(e for e in events if e["event"] == "summary")
    payload = json.loads(summary_event["data"])
    assert "summary" in payload
    assert isinstance(payload["summary"], str)
    assert len(payload["summary"]) > 0


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_no_summary_event_for_short_history(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """generate_answer_stream should not emit a summary event for short history."""
    settings = _test_settings(tmp_path)
    history = _make_messages(4)

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        history=history,
        llm_provider=FakeLLMProvider(),
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    event_types = [e["event"] for e in events]
    assert "summary" not in event_types


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_summary_event_order(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """summary event should appear after citations and before done."""
    settings = _test_settings(tmp_path)
    history = _make_messages(10)

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        history=history,
        llm_provider=FakeLLMProvider(),
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    event_types = [e["event"] for e in events]

    citations_idx = event_types.index("citations")
    summary_idx = event_types.index("summary")
    done_idx = event_types.index("done")
    assert citations_idx < summary_idx < done_idx


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_fallback_truncation_on_summarization_failure(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """When summarization fails, no summary event should be emitted and generation still works."""
    settings = _test_settings(tmp_path)
    history = _make_messages(10)

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        history=history,
        llm_provider=FailingLLMProvider(),
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    event_types = [e["event"] for e in events]

    # No summary event since summarization failed
    assert "summary" not in event_types
    # But generation should still complete
    assert "done" in event_types
    assert "token" in event_types
