"""Query rewriter plugin — rephrase user queries before retrieval.

Applies simple rule-based HyDE-style rewriting:
- Expands common abbreviations (ML, AI, NLP, etc.)
- Prepends "Please explain" for very short queries (< 5 words)
- Lowercases the query for better matching

This is an MVP approach; LLM-based rewriting would be a future enhancement.
"""

from __future__ import annotations

import re

from app.plugins.base import PluginBase

# Common abbreviations mapped to their expansions.
_ABBREVIATIONS: dict[str, str] = {
    "ML": "machine learning",
    "AI": "artificial intelligence",
    "NLP": "natural language processing",
    "LLM": "large language model",
    "API": "application programming interface",
    "DB": "database",
    "SQL": "structured query language",
    "ORM": "object relational mapping",
    "CLI": "command line interface",
    "UI": "user interface",
    "UX": "user experience",
    "RAG": "retrieval augmented generation",
    "OCR": "optical character recognition",
    "CV": "computer vision",
    "RL": "reinforcement learning",
    "DL": "deep learning",
}

# Pre-compile a regex that matches any abbreviation as a whole word (case-insensitive).
_ABBREV_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _ABBREVIATIONS) + r")\b",
    re.IGNORECASE,
)

_SHORT_QUERY_THRESHOLD = 5


class QueryRewriterPlugin(PluginBase):
    """Rephrase user queries before retrieval using simple rules."""

    name: str = "query_rewriter"
    description: str = "Rephrase user queries before retrieval (HyDE-style)"

    def on_retrieve(self, query: str) -> str:
        """Rewrite *query* by expanding abbreviations, lowering case, etc."""
        if not query or not query.strip():
            return query

        rewritten = query.strip()

        # Expand abbreviations (preserving surrounding text).
        rewritten = _ABBREV_PATTERN.sub(lambda m: _ABBREVIATIONS[m.group(0).upper()], rewritten)

        # Lowercase for better embedding / BM25 matching.
        rewritten = rewritten.lower()

        # Prefix short queries with "please explain" to encourage richer retrieval.
        word_count = len(rewritten.split())
        if word_count < _SHORT_QUERY_THRESHOLD:
            rewritten = f"please explain {rewritten}"

        return rewritten


def register(app: object) -> QueryRewriterPlugin:
    """Factory called by the plugin loader to register this plugin.

    Args:
        app: The FastAPI application instance (unused for now).

    Returns:
        An instance of :class:`QueryRewriterPlugin`.
    """
    return QueryRewriterPlugin()
