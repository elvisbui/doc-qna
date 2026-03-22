"""Tests for the plugin base class and hook protocol."""

from app.plugins.base import PluginBase

# ---------------------------------------------------------------------------
# Default no-op behaviour
# ---------------------------------------------------------------------------


class TestPluginBaseDefaults:
    """PluginBase methods should return their inputs unchanged."""

    def test_default_name_and_description(self):
        plugin = PluginBase()
        assert plugin.name == "unnamed_plugin"
        assert plugin.description == ""

    def test_enabled_by_default(self):
        plugin = PluginBase()
        assert plugin.enabled is True

    def test_on_chunk_noop(self):
        plugin = PluginBase()
        assert plugin.on_chunk("hello", {"page": 1}) == "hello"

    def test_on_ingest_noop(self):
        plugin = PluginBase()
        chunks = ["a", "b", "c"]
        assert plugin.on_ingest("doc-1", chunks) is chunks

    def test_on_retrieve_noop(self):
        plugin = PluginBase()
        assert plugin.on_retrieve("some query") == "some query"

    def test_on_post_retrieve_noop(self):
        plugin = PluginBase()
        results = [{"id": 1, "score": 0.9}]
        assert plugin.on_post_retrieve("q", results) is results

    def test_on_generate_noop(self):
        plugin = PluginBase()
        assert plugin.on_generate("prompt", "context") == ("prompt", "context")

    def test_on_post_generate_noop(self):
        plugin = PluginBase()
        assert plugin.on_post_generate("answer") == "answer"


# ---------------------------------------------------------------------------
# Subclass overriding specific hooks
# ---------------------------------------------------------------------------


class UpperCaseChunkPlugin(PluginBase):
    """Example plugin that upper-cases chunk text."""

    name = "upper_chunk"
    description = "Converts chunk text to upper case."

    def on_chunk(self, text: str, metadata: dict) -> str:
        return text.upper()


class QueryPrefixPlugin(PluginBase):
    """Example plugin that prepends a prefix to queries."""

    name = "query_prefix"
    description = "Adds a prefix to retrieval queries."

    def on_retrieve(self, query: str) -> str:
        return f"[enhanced] {query}"


class TestSubclassOverrides:
    def test_upper_chunk_plugin(self):
        plugin = UpperCaseChunkPlugin()
        assert plugin.name == "upper_chunk"
        assert plugin.on_chunk("hello world", {}) == "HELLO WORLD"
        # Other hooks remain no-op
        assert plugin.on_retrieve("q") == "q"
        assert plugin.on_post_generate("ans") == "ans"

    def test_query_prefix_plugin(self):
        plugin = QueryPrefixPlugin()
        assert plugin.on_retrieve("what is X?") == "[enhanced] what is X?"
        # on_chunk is still no-op
        assert plugin.on_chunk("text", {}) == "text"

    def test_subclass_can_disable(self):
        plugin = UpperCaseChunkPlugin()
        plugin.enabled = False
        assert plugin.enabled is False


# ---------------------------------------------------------------------------
# Multiple hooks on one plugin
# ---------------------------------------------------------------------------


class MultiHookPlugin(PluginBase):
    """Plugin overriding several hooks at once."""

    name = "multi"
    description = "Demonstrates multiple hooks."

    def on_chunk(self, text: str, metadata: dict) -> str:
        return text.strip()

    def on_ingest(self, document_id: str, chunks: list[str]) -> list[str]:
        return [c for c in chunks if c]  # drop empty chunks

    def on_retrieve(self, query: str) -> str:
        return query.lower()

    def on_post_retrieve(self, query: str, results: list[dict]) -> list[dict]:
        return sorted(results, key=lambda r: r.get("score", 0), reverse=True)

    def on_generate(self, prompt: str, context: str) -> tuple[str, str]:
        return prompt, f"[context] {context}"

    def on_post_generate(self, answer: str) -> str:
        return answer.rstrip(".")


class TestMultipleHooks:
    def test_on_chunk(self):
        p = MultiHookPlugin()
        assert p.on_chunk("  spaced  ", {}) == "spaced"

    def test_on_ingest_filters_empty(self):
        p = MultiHookPlugin()
        assert p.on_ingest("d1", ["a", "", "b"]) == ["a", "b"]

    def test_on_retrieve_lowercases(self):
        p = MultiHookPlugin()
        assert p.on_retrieve("HELLO") == "hello"

    def test_on_post_retrieve_sorts(self):
        p = MultiHookPlugin()
        results = [{"score": 0.5}, {"score": 0.9}]
        assert p.on_post_retrieve("q", results) == [{"score": 0.9}, {"score": 0.5}]

    def test_on_generate_prefixes_context(self):
        p = MultiHookPlugin()
        assert p.on_generate("p", "c") == ("p", "[context] c")

    def test_on_post_generate_strips_dot(self):
        p = MultiHookPlugin()
        assert p.on_post_generate("done.") == "done"
