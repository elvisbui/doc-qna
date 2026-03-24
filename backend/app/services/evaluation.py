"""Evaluation framework — automated RAG quality metrics.

Provides lightweight, pure-Python metrics for measuring retrieval and
generation quality without requiring external evaluation libraries or
LLM calls.  Designed for offline batch evaluation and CI integration.

Metrics
-------
- **Retrieval Relevance**: mean relevance score across returned citations.
- **Context Coverage**: fraction of citations whose relevance score meets
  or exceeds a configurable threshold (default 0.5).
- **Answer Groundedness**: bag-of-words overlap between the generated
  answer and the concatenated citation content (stopword-filtered).
"""

from __future__ import annotations

import re
import statistics
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.models import Citation

# fmt: off
_STOPWORDS: frozenset[str] = frozenset({
    "a", "about", "after", "again", "all", "also", "an", "and", "are",
    "aren", "as", "at", "be", "been", "before", "being", "between", "both",
    "but", "by", "can", "could", "did", "didn", "do", "does", "doesn",
    "don", "each", "every", "few", "for", "from", "had", "hadn", "has",
    "hasn", "have", "haven", "he", "her", "here", "his", "how", "i", "if",
    "in", "into", "is", "isn", "it", "its", "just", "may", "me", "might",
    "more", "most", "my", "no", "not", "now", "of", "on", "once", "only",
    "or", "other", "our", "out", "over", "s", "shall", "she", "should",
    "shouldn", "so", "some", "such", "t", "than", "that", "the", "them",
    "then", "there", "these", "they", "this", "those", "to", "too", "under",
    "up", "very", "was", "wasn", "we", "were", "weren", "what", "when",
    "where", "which", "who", "whom", "why", "will", "with", "won", "would",
    "wouldn", "you", "your",
})
# fmt: on

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    """Return a set of lowercase, stopword-filtered tokens."""
    return {tok for tok in _TOKEN_RE.findall(text.lower()) if tok not in _STOPWORDS and len(tok) > 1}


@dataclass(frozen=True, slots=True)
class EvalResult:
    """Evaluation result for a single query–answer pair."""

    query: str
    retrieval_relevance: float
    context_coverage: float
    groundedness: float
    confidence: float
    num_citations: int
    abstained: bool


def _retrieval_relevance(citations: list[Citation]) -> float:
    """Average relevance score of returned citations.

    Returns 0.0 when there are no citations.
    """
    if not citations:
        return 0.0
    return statistics.mean(c.relevance_score for c in citations)


def _context_coverage(citations: list[Citation], threshold: float = 0.5) -> float:
    """Fraction of citations with a relevance score >= *threshold*.

    Returns 0.0 when there are no citations.
    """
    if not citations:
        return 0.0
    above = sum(c.relevance_score >= threshold for c in citations)
    return above / len(citations)


def _groundedness(answer: str, citations: list[Citation]) -> float:
    """Bag-of-words overlap between the answer and retrieved context.

    Computes the fraction of non-stopword tokens in *answer* that also
    appear somewhere in the concatenated citation content.

    Returns 1.0 when the answer is empty or contains only stopwords
    (vacuously grounded), and 0.0 when there are no citations.
    """
    answer_tokens = _tokenize(answer)
    if not answer_tokens:
        return 1.0
    if not citations:
        return 0.0
    context_tokens = _tokenize(" ".join(c.chunk_content for c in citations))
    overlap = answer_tokens & context_tokens
    return len(overlap) / len(answer_tokens)


def evaluate_single(
    query: str,
    answer: str,
    citations: list[Citation],
    confidence: float,
    relevance_threshold: float = 0.5,
) -> EvalResult:
    """Evaluate a single RAG query–answer pair.

    Args:
        query: The user's original question.
        answer: The generated answer text.
        citations: Citations returned by the retrieval service.
        confidence: Confidence score produced by the confidence service.
        relevance_threshold: Minimum relevance score for a citation to
            count toward context coverage.

    Returns:
        An ``EvalResult`` containing all computed metrics.
    """
    from app.services.confidence import should_abstain

    return EvalResult(
        query=query,
        retrieval_relevance=_retrieval_relevance(citations),
        context_coverage=_context_coverage(citations, relevance_threshold),
        groundedness=_groundedness(answer, citations),
        confidence=confidence,
        num_citations=len(citations),
        abstained=should_abstain(confidence),
    )


def summarize_results(results: list[EvalResult]) -> dict:
    """Compute aggregate statistics over a list of evaluation results.

    Returns a dict with the following structure::

        {
            "count": int,
            "abstained_count": int,
            "retrieval_relevance": {"mean": ..., "min": ..., "max": ...},
            "context_coverage":    {"mean": ..., "min": ..., "max": ...},
            "groundedness":        {"mean": ..., "min": ..., "max": ...},
            "confidence":          {"mean": ..., "min": ..., "max": ...},
            "num_citations":       {"mean": ..., "min": ..., "max": ...},
        }

    Returns an empty summary dict when *results* is empty.
    """
    if not results:
        return {
            "count": 0,
            "abstained_count": 0,
            "retrieval_relevance": {"mean": 0.0, "min": 0.0, "max": 0.0},
            "context_coverage": {"mean": 0.0, "min": 0.0, "max": 0.0},
            "groundedness": {"mean": 0.0, "min": 0.0, "max": 0.0},
            "confidence": {"mean": 0.0, "min": 0.0, "max": 0.0},
            "num_citations": {"mean": 0.0, "min": 0.0, "max": 0.0},
        }

    def _agg(values: list[float]) -> dict:
        return {
            "mean": statistics.mean(values),
            "min": min(values),
            "max": max(values),
        }

    return {
        "count": len(results),
        "abstained_count": sum(r.abstained for r in results),
        "retrieval_relevance": _agg([r.retrieval_relevance for r in results]),
        "context_coverage": _agg([r.context_coverage for r in results]),
        "groundedness": _agg([r.groundedness for r in results]),
        "confidence": _agg([r.confidence for r in results]),
        "num_citations": _agg([float(r.num_citations) for r in results]),
    }
