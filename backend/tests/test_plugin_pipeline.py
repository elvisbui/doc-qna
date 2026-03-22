"""Tests for the plugin execution pipeline."""

from __future__ import annotations

from app.plugins.base import PluginBase
from app.plugins.pipeline import PluginPipeline

# ---------------------------------------------------------------------------
# Helper plugins
# ---------------------------------------------------------------------------


class UpperCasePlugin(PluginBase):
    name = "upper"
    description = "Uppercases chunk text"

    def on_chunk(self, text: str, metadata: dict) -> str:
        return text.upper()

    def on_retrieve(self, query: str) -> str:
        return query.upper()

    def on_post_generate(self, answer: str) -> str:
        return answer.upper()

    def on_generate(self, prompt: str, context: str) -> tuple[str, str]:
        return prompt.upper(), context.upper()


class SuffixPlugin(PluginBase):
    name = "suffix"
    description = "Appends a suffix"

    def on_chunk(self, text: str, metadata: dict) -> str:
        return text + "_suffix"

    def on_retrieve(self, query: str) -> str:
        return query + "_suffix"

    def on_post_generate(self, answer: str) -> str:
        return answer + "_suffix"

    def on_ingest(self, document_id: str, chunks: list[str]) -> list[str]:
        return [c + "_suffix" for c in chunks]

    def on_post_retrieve(self, query: str, results: list[dict]) -> list[dict]:
        return results + [{"id": "extra", "query": query}]


class BrokenPlugin(PluginBase):
    name = "broken"
    description = "Always raises"

    def on_chunk(self, text: str, metadata: dict) -> str:
        raise RuntimeError("boom")

    def on_retrieve(self, query: str) -> str:
        raise ValueError("oops")

    def on_generate(self, prompt: str, context: str) -> tuple[str, str]:
        raise RuntimeError("generate-boom")

    def on_post_generate(self, answer: str) -> str:
        raise RuntimeError("post-generate-boom")


# ---------------------------------------------------------------------------
# Tests — single plugin dispatch
# ---------------------------------------------------------------------------


class TestSinglePlugin:
    def test_on_chunk(self):
        pipeline = PluginPipeline([UpperCasePlugin()])
        result = pipeline.run_on_chunk("hello", {"key": "val"})
        assert result == "HELLO"

    def test_on_retrieve(self):
        pipeline = PluginPipeline([UpperCasePlugin()])
        result = pipeline.run_on_retrieve("find me")
        assert result == "FIND ME"

    def test_on_generate_returns_tuple(self):
        pipeline = PluginPipeline([UpperCasePlugin()])
        result = pipeline.run_on_generate("prompt", "context")
        assert result == ("PROMPT", "CONTEXT")

    def test_on_post_generate(self):
        pipeline = PluginPipeline([SuffixPlugin()])
        result = pipeline.run_on_post_generate("answer")
        assert result == "answer_suffix"

    def test_on_ingest(self):
        pipeline = PluginPipeline([SuffixPlugin()])
        result = pipeline.run_on_ingest("doc1", ["a", "b"])
        assert result == ["a_suffix", "b_suffix"]

    def test_on_post_retrieve(self):
        pipeline = PluginPipeline([SuffixPlugin()])
        result = pipeline.run_on_post_retrieve("q", [{"id": "1"}])
        assert len(result) == 2
        assert result[-1]["id"] == "extra"


# ---------------------------------------------------------------------------
# Tests — chained plugins (output feeds into next)
# ---------------------------------------------------------------------------


class TestChainedPlugins:
    def test_on_chunk_chained(self):
        pipeline = PluginPipeline([UpperCasePlugin(), SuffixPlugin()])
        result = pipeline.run_on_chunk("hello", {})
        assert result == "HELLO_suffix"

    def test_on_retrieve_chained(self):
        pipeline = PluginPipeline([SuffixPlugin(), UpperCasePlugin()])
        result = pipeline.run_on_retrieve("query")
        assert result == "QUERY_SUFFIX"

    def test_on_generate_chained(self):
        pipeline = PluginPipeline([UpperCasePlugin(), UpperCasePlugin()])
        result = pipeline.run_on_generate("p", "c")
        assert result == ("P", "C")

    def test_on_post_generate_chained(self):
        pipeline = PluginPipeline([UpperCasePlugin(), SuffixPlugin()])
        result = pipeline.run_on_post_generate("hi")
        assert result == "HI_suffix"


# ---------------------------------------------------------------------------
# Tests — error isolation
# ---------------------------------------------------------------------------


class TestErrorIsolation:
    def test_broken_plugin_skipped_on_chunk(self):
        pipeline = PluginPipeline([BrokenPlugin(), SuffixPlugin()])
        result = pipeline.run_on_chunk("text", {})
        assert result == "text_suffix"

    def test_broken_plugin_skipped_on_retrieve(self):
        pipeline = PluginPipeline([BrokenPlugin(), UpperCasePlugin()])
        result = pipeline.run_on_retrieve("hello")
        assert result == "HELLO"

    def test_broken_in_middle(self):
        pipeline = PluginPipeline([UpperCasePlugin(), BrokenPlugin(), SuffixPlugin()])
        result = pipeline.run_on_chunk("hi", {})
        assert result == "HI_suffix"

    def test_all_broken_returns_original(self):
        pipeline = PluginPipeline([BrokenPlugin(), BrokenPlugin()])
        result = pipeline.run_on_chunk("original", {})
        assert result == "original"

    def test_broken_on_generate(self):
        pipeline = PluginPipeline([BrokenPlugin(), UpperCasePlugin()])
        result = pipeline.run_on_generate("p", "c")
        assert result == ("P", "C")

    def test_broken_on_post_generate(self):
        pipeline = PluginPipeline([BrokenPlugin(), SuffixPlugin()])
        result = pipeline.run_on_post_generate("ans")
        assert result == "ans_suffix"


# ---------------------------------------------------------------------------
# Tests — execution trace
# ---------------------------------------------------------------------------


class TestExecutionTrace:
    def test_trace_records_entries(self):
        pipeline = PluginPipeline([UpperCasePlugin()])
        pipeline.run_on_chunk("x", {})
        trace = pipeline.get_trace()
        assert len(trace) == 1
        assert trace[0]["plugin"] == "upper"
        assert trace[0]["hook"] == "on_chunk"
        assert trace[0]["error"] is False
        assert "duration_ms" in trace[0]

    def test_trace_multiple_hooks(self):
        pipeline = PluginPipeline([UpperCasePlugin(), SuffixPlugin()])
        pipeline.run_on_chunk("x", {})
        trace = pipeline.get_trace()
        assert len(trace) == 2
        assert trace[0]["plugin"] == "upper"
        assert trace[1]["plugin"] == "suffix"

    def test_trace_records_errors(self):
        pipeline = PluginPipeline([BrokenPlugin(), SuffixPlugin()])
        pipeline.run_on_chunk("x", {})
        trace = pipeline.get_trace()
        assert len(trace) == 2
        assert trace[0]["error"] is True
        assert trace[1]["error"] is False

    def test_clear_trace(self):
        pipeline = PluginPipeline([UpperCasePlugin()])
        pipeline.run_on_chunk("x", {})
        assert len(pipeline.get_trace()) == 1
        pipeline.clear_trace()
        assert len(pipeline.get_trace()) == 0

    def test_trace_accumulates_across_calls(self):
        pipeline = PluginPipeline([UpperCasePlugin()])
        pipeline.run_on_chunk("a", {})
        pipeline.run_on_retrieve("b")
        trace = pipeline.get_trace()
        assert len(trace) == 2
        assert trace[0]["hook"] == "on_chunk"
        assert trace[1]["hook"] == "on_retrieve"

    def test_disabled_plugin_not_traced(self):
        plugin = UpperCasePlugin()
        plugin.enabled = False
        pipeline = PluginPipeline([plugin])
        pipeline.run_on_chunk("x", {})
        assert len(pipeline.get_trace()) == 0

    def test_get_trace_returns_copy(self):
        pipeline = PluginPipeline([UpperCasePlugin()])
        pipeline.run_on_chunk("x", {})
        trace = pipeline.get_trace()
        trace.clear()
        assert len(pipeline.get_trace()) == 1


# ---------------------------------------------------------------------------
# Tests — disabled plugins
# ---------------------------------------------------------------------------


class TestDisabledPlugins:
    def test_disabled_plugin_skipped(self):
        plugin = UpperCasePlugin()
        plugin.enabled = False
        pipeline = PluginPipeline([plugin, SuffixPlugin()])
        result = pipeline.run_on_chunk("hello", {})
        assert result == "hello_suffix"

    def test_empty_pipeline(self):
        pipeline = PluginPipeline([])
        result = pipeline.run_on_chunk("hello", {})
        assert result == "hello"

    def test_empty_pipeline_generate(self):
        pipeline = PluginPipeline([])
        result = pipeline.run_on_generate("p", "c")
        assert result == ("p", "c")
