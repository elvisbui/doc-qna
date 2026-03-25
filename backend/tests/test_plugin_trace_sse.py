"""Tests for plugin trace SSE events in the chat stream."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.plugins.base import PluginBase
from app.plugins.pipeline import PluginPipeline
from app.services.generation import generate_answer_stream

# ---------------------------------------------------------------------------
# Fake providers
# ---------------------------------------------------------------------------


class FakeLLMProvider:
    """Fake LLM that echoes the query back as a streamed answer."""

    async def generate_stream(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        yield "Hello "
        yield "world"


class TimingPlugin(PluginBase):
    name = "timing_test"
    description = "A test plugin"

    def on_post_generate(self, answer: str) -> str:
        return answer + " [processed]"


class ErrorPlugin(PluginBase):
    name = "error_test"
    description = "A plugin that errors"

    def on_post_generate(self, answer: str) -> str:
        raise RuntimeError("plugin failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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


# Patch retrieval to return empty citations (no real embedding needed)
_mock_retrieve = AsyncMock(return_value=[])


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
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_plugin_trace_event_emitted(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """generate_answer_stream should emit a plugin_trace SSE event when a pipeline is provided."""
    settings = _test_settings(tmp_path)
    pipeline = PluginPipeline([TimingPlugin()])

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        llm_provider=FakeLLMProvider(),
        plugin_pipeline=pipeline,
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    event_types = [e["event"] for e in events]
    assert "plugin_trace" in event_types, f"Expected plugin_trace event, got: {event_types}"

    trace_event = next(e for e in events if e["event"] == "plugin_trace")
    trace_data = json.loads(trace_event["data"])
    assert isinstance(trace_data, list)
    assert len(trace_data) >= 1
    # Find the on_post_generate entry (other hooks like on_retrieve/on_generate may also appear)
    post_gen = [t for t in trace_data if t["hookName"] == "on_post_generate"]
    assert len(post_gen) == 1
    assert post_gen[0]["pluginName"] == "timing_test"
    assert "durationMs" in post_gen[0]
    assert post_gen[0]["error"] is False


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_plugin_trace_records_errors(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """Plugin trace should record errors from plugins that raise."""
    settings = _test_settings(tmp_path)
    pipeline = PluginPipeline([ErrorPlugin()])

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        llm_provider=FakeLLMProvider(),
        plugin_pipeline=pipeline,
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    trace_event = next(e for e in events if e["event"] == "plugin_trace")
    trace_data = json.loads(trace_event["data"])
    assert len(trace_data) >= 1
    # Find the on_post_generate entry which is the one that errors
    post_gen = [t for t in trace_data if t["hookName"] == "on_post_generate"]
    assert len(post_gen) == 1
    assert post_gen[0]["error"] is True


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_plugin_trace_not_emitted_without_pipeline(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """Without a plugin pipeline, no plugin_trace event should be emitted."""
    settings = _test_settings(tmp_path)

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        llm_provider=FakeLLMProvider(),
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    event_types = [e["event"] for e in events]
    assert "plugin_trace" not in event_types


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_plugin_trace_event_order(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """plugin_trace should appear after citations and before done."""
    settings = _test_settings(tmp_path)
    pipeline = PluginPipeline([TimingPlugin()])

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        llm_provider=FakeLLMProvider(),
        plugin_pipeline=pipeline,
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    event_types = [e["event"] for e in events]

    # plugin_trace should come after citations
    citations_idx = event_types.index("citations")
    trace_idx = event_types.index("plugin_trace")
    done_idx = event_types.index("done")
    assert citations_idx < trace_idx < done_idx


@pytest.mark.asyncio
@patch("app.services.generation.should_abstain", return_value=False)
@patch("app.services.generation.retrieve_relevant_chunks", new_callable=AsyncMock, return_value=[])
@patch("app.services.generation.build_generation_kwargs", return_value={})
async def test_plugin_trace_empty_pipeline(_mock_kwargs, _mock_retrieval, _mock_abstain, tmp_path):
    """An empty pipeline should emit plugin_trace with an empty list."""
    settings = _test_settings(tmp_path)
    pipeline = PluginPipeline([])

    events_text = ""
    async for event in generate_answer_stream(
        "test query",
        settings,
        collection=None,
        llm_provider=FakeLLMProvider(),
        plugin_pipeline=pipeline,
    ):
        events_text += event

    events = _parse_sse_events(events_text)
    trace_event = next(e for e in events if e["event"] == "plugin_trace")
    trace_data = json.loads(trace_event["data"])
    assert trace_data == []
