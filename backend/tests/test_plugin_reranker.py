"""Tests for the reranker plugin."""

from app.plugins.reranker import RerankerPlugin, register


class TestRerankerPlugin:
    """Unit tests for RerankerPlugin."""

    def _make_result(self, content: str, relevance_score: float) -> dict:
        return {
            "content": content,
            "metadata": {},
            "relevance_score": relevance_score,
        }

    def test_reranking_changes_order(self):
        """Results with higher keyword overlap should be promoted."""
        plugin = RerankerPlugin()

        results = [
            self._make_result("The weather is nice today", relevance_score=0.9),
            self._make_result("Python machine learning tutorial", relevance_score=0.5),
        ]

        reranked = plugin.on_post_retrieve("Python machine learning", results)

        # The second result has much higher keyword overlap with the query,
        # so it should be promoted to the top despite a lower original score.
        assert reranked[0]["content"] == "Python machine learning tutorial"
        assert reranked[1]["content"] == "The weather is nice today"

    def test_query_word_overlap_scoring(self):
        """Rerank score should reflect the fraction of query words found."""
        plugin = RerankerPlugin()

        results = [
            self._make_result("apple banana cherry", relevance_score=0.5),
        ]

        reranked = plugin.on_post_retrieve("apple banana", results)

        # Both query words appear -> rerank_score = 2/2 = 1.0
        assert reranked[0]["rerank_score"] == 1.0
        # final_score = 0.6 * 0.5 + 0.4 * 1.0 = 0.7
        assert abs(reranked[0]["final_score"] - 0.7) < 1e-9

    def test_partial_overlap_scoring(self):
        """Only some query words match."""
        plugin = RerankerPlugin()

        results = [
            self._make_result("apple pie recipe", relevance_score=0.5),
        ]

        reranked = plugin.on_post_retrieve("apple banana cherry", results)

        # 1 out of 3 query words -> rerank_score = 1/3
        assert abs(reranked[0]["rerank_score"] - 1 / 3) < 1e-9

    def test_empty_results(self):
        """Empty results should be returned as-is."""
        plugin = RerankerPlugin()
        assert plugin.on_post_retrieve("some query", []) == []

    def test_empty_query(self):
        """Empty query should return results unchanged (no reranking)."""
        plugin = RerankerPlugin()
        results = [
            self._make_result("content a", relevance_score=0.8),
            self._make_result("content b", relevance_score=0.5),
        ]
        reranked = plugin.on_post_retrieve("", results)
        # Order preserved
        assert reranked[0]["content"] == "content a"
        assert reranked[1]["content"] == "content b"

    def test_distance_key_support(self):
        """Results with 'distance' instead of 'relevance_score' should work."""
        plugin = RerankerPlugin()
        results = [
            {"content": "hello world", "metadata": {}, "distance": 0.0},
        ]
        reranked = plugin.on_post_retrieve("hello world", results)
        # distance=0 -> relevance=1/(1+0)=1.0, rerank=1.0
        # final = 0.6*1.0 + 0.4*1.0 = 1.0
        assert abs(reranked[0]["final_score"] - 1.0) < 1e-9

    def test_register_function(self):
        """register() should return a RerankerPlugin instance."""
        plugin = register(app=None)
        assert isinstance(plugin, RerankerPlugin)
        assert plugin.name == "reranker"

    def test_plugin_attributes(self):
        """Plugin should have correct name and description."""
        plugin = RerankerPlugin()
        assert plugin.name == "reranker"
        assert "reranking" in plugin.description.lower() or "rerank" in plugin.description.lower()
