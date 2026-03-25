"""Tests for the query_rewriter plugin."""

from __future__ import annotations

import pytest

from app.plugins.query_rewriter import QueryRewriterPlugin, register


@pytest.fixture
def plugin() -> QueryRewriterPlugin:
    return QueryRewriterPlugin()


# -- Abbreviation expansion ---------------------------------------------------


class TestAbbreviationExpansion:
    def test_expands_ml(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("What is ML used for in practice?")
        assert "machine learning" in result
        assert "ml" not in result.split()  # abbreviation should be replaced

    def test_expands_ai(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("How does AI work in production systems?")
        assert "artificial intelligence" in result

    def test_expands_nlp(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("NLP techniques for text classification")
        assert "natural language processing" in result

    def test_expands_llm(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("How to fine-tune an LLM for summarization?")
        assert "large language model" in result

    def test_expands_multiple_abbreviations(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("Compare ML and NLP approaches in modern AI")
        assert "machine learning" in result
        assert "natural language processing" in result
        assert "artificial intelligence" in result

    def test_expansion_is_case_insensitive(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("What is ml and what is Ai in this context?")
        assert "machine learning" in result
        assert "artificial intelligence" in result

    def test_expands_rag(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("Explain RAG pipelines for document search tasks")
        assert "retrieval augmented generation" in result


# -- Short query expansion ----------------------------------------------------


class TestShortQueryExpansion:
    def test_short_query_gets_prefix(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("transformers")
        assert result.startswith("please explain")
        assert "transformers" in result

    def test_four_word_query_gets_prefix(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("What is deep learning")
        assert result.startswith("please explain")

    def test_five_word_query_no_prefix(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("What is deep learning exactly")
        assert not result.startswith("please explain")

    def test_long_query_no_prefix(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("How do transformer models handle long sequences?")
        assert not result.startswith("please explain")


# -- Passthrough / edge cases --------------------------------------------------


class TestPassthrough:
    def test_normal_query_lowercased(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("How do neural networks learn representations?")
        assert result == "how do neural networks learn representations?"

    def test_empty_string_passthrough(self, plugin: QueryRewriterPlugin) -> None:
        assert plugin.on_retrieve("") == ""

    def test_whitespace_only_passthrough(self, plugin: QueryRewriterPlugin) -> None:
        assert plugin.on_retrieve("   ") == "   "

    def test_result_is_lowercased(self, plugin: QueryRewriterPlugin) -> None:
        result = plugin.on_retrieve("Explain The Concept Of Backpropagation In Detail")
        assert result == result.lower()

    def test_inherits_plugin_base(self, plugin: QueryRewriterPlugin) -> None:
        from app.plugins.base import PluginBase

        assert isinstance(plugin, PluginBase)

    def test_plugin_name(self, plugin: QueryRewriterPlugin) -> None:
        assert plugin.name == "query_rewriter"

    def test_plugin_description(self, plugin: QueryRewriterPlugin) -> None:
        assert "HyDE" in plugin.description

    def test_enabled_by_default(self, plugin: QueryRewriterPlugin) -> None:
        assert plugin.enabled is True


# -- register function --------------------------------------------------------


class TestRegister:
    def test_register_returns_plugin_instance(self) -> None:
        instance = register(app=None)
        assert isinstance(instance, QueryRewriterPlugin)
