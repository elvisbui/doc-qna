"""Tests for the summarizer plugin."""

from app.plugins.summarizer import SummarizerPlugin, _first_sentence, register


class TestFirstSentence:
    """Unit tests for the _first_sentence helper."""

    def test_simple_sentence(self):
        assert _first_sentence("Hello world. More text.") == "Hello world."

    def test_exclamation(self):
        assert _first_sentence("Wow! That was great.") == "Wow!"

    def test_question(self):
        assert _first_sentence("Is this working? Yes.") == "Is this working?"

    def test_no_punctuation(self):
        assert _first_sentence("No ending punctuation") == "No ending punctuation"

    def test_empty_string(self):
        assert _first_sentence("") == ""

    def test_whitespace_only(self):
        assert _first_sentence("   ") == ""


class TestSummarizerPlugin:
    """Tests for SummarizerPlugin.on_ingest."""

    def setup_method(self):
        self.plugin = SummarizerPlugin()

    def test_name_and_description(self):
        assert self.plugin.name == "summarizer"
        assert self.plugin.description == "Auto-generate a document summary on ingest"

    def test_summary_is_prepended(self):
        chunks = ["First chunk. Details here.", "Second chunk. More info."]
        result = self.plugin.on_ingest("doc-1", chunks)
        assert len(result) == 3
        assert result[0].startswith("[SUMMARY] ")
        assert result[1:] == chunks

    def test_summary_content(self):
        chunks = [
            "The sky is blue. It is vast.",
            "Water is wet. It flows downhill.",
        ]
        result = self.plugin.on_ingest("doc-1", chunks)
        summary = result[0]
        assert summary == "[SUMMARY] The sky is blue. Water is wet."

    def test_empty_chunks(self):
        result = self.plugin.on_ingest("doc-1", [])
        assert result == []

    def test_single_chunk(self):
        chunks = ["Only one sentence here."]
        result = self.plugin.on_ingest("doc-1", chunks)
        assert len(result) == 2
        assert result[0] == "[SUMMARY] Only one sentence here."
        assert result[1] == chunks[0]

    def test_chunks_with_blank_entries(self):
        chunks = ["Good text. More.", "", "   ", "Another chunk."]
        result = self.plugin.on_ingest("doc-1", chunks)
        # Blank chunks produce empty first-sentences which are filtered out.
        assert result[0] == "[SUMMARY] Good text. Another chunk."
        assert result[1:] == chunks

    def test_original_chunks_unchanged(self):
        chunks = ["Alpha. Beta.", "Gamma. Delta."]
        original = list(chunks)
        self.plugin.on_ingest("doc-1", chunks)
        assert chunks == original


class TestRegister:
    """Tests for the module-level register function."""

    def test_register_returns_plugin(self):
        plugin = register(None)
        assert isinstance(plugin, SummarizerPlugin)
        assert plugin.enabled is True
