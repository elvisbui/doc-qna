"""Reranker plugin — keyword-overlap reranking via on_post_retrieve hook."""

from __future__ import annotations

import re

from app.plugins.base import PluginBase


class RerankerPlugin(PluginBase):
    """Cross-encoder style reranking via on_post_retrieve hook.

    For the MVP this uses simple keyword-overlap scoring rather than a real
    cross-encoder model.  The final score blends the original relevance with
    the overlap-based rerank score.
    """

    name: str = "reranker"
    description: str = "Cross-encoder style reranking via on_post_retrieve hook"

    _WORD_RE = re.compile(r"\w+")

    def on_post_retrieve(self, query: str, results: list[dict]) -> list[dict]:
        """Rerank *results* using keyword overlap with *query*.

        Scoring
        -------
        1. Tokenize the query into lowercase words.
        2. For each result, count how many query words appear in its content.
        3. ``rerank_score = overlap_count / len(query_words)``  (0 when query
           is empty).
        4. ``final_score = 0.6 * original_relevance + 0.4 * rerank_score``
        5. Sort descending by ``final_score``.
        """
        if not results:
            return results

        query_words = [w.lower() for w in self._WORD_RE.findall(query)]
        if not query_words:
            return results

        scored: list[tuple[float, int, dict]] = []
        for idx, result in enumerate(results):
            content_lower = result.get("content", "").lower()
            overlap_count = sum(1 for w in query_words if w in content_lower)
            rerank_score = overlap_count / len(query_words)

            # Support both 'relevance_score' and 'distance' keys.
            # distance is inverse relevance (lower = better), so convert.
            if "relevance_score" in result:
                original_relevance = float(result["relevance_score"])
            elif "distance" in result:
                # Convert distance to a 0-1 relevance value.
                original_relevance = 1.0 / (1.0 + float(result["distance"]))
            else:
                original_relevance = 0.0

            final_score = 0.6 * original_relevance + 0.4 * rerank_score

            updated = {**result, "final_score": final_score, "rerank_score": rerank_score}
            # Use -idx as tiebreaker to preserve original order for equal scores
            scored.append((final_score, -idx, updated))

        scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return [item for _, _, item in scored]


def register(app: object) -> RerankerPlugin:
    """Factory function expected by the plugin loader."""
    return RerankerPlugin()
