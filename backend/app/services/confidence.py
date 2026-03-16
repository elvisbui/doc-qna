"""Confidence scoring service for RAG answer quality estimation.

Estimates how confident we should be in a RAG answer based on the
retrieved chunks. Used to decide whether to answer or say "I don't know."
"""

import statistics

from app.core.models import Citation


def calculate_confidence(citations: list[Citation]) -> float:
    """Return a confidence score between 0.0 and 1.0 based on citation quality.

    The score is a weighted heuristic combining:
      - Number of relevant citations (more = higher confidence)
      - Average relevance score across citations
      - Consistency of relevance scores (low spread = higher confidence)

    Args:
        citations: Retrieved ``Citation`` objects with ``relevance_score``
            attributes. An empty list yields a score of ``0.0``.

    Returns:
        A float in ``[0.0, 1.0]`` representing the estimated answer
        confidence. Higher values indicate stronger retrieval evidence.
    """
    if not citations:
        return 0.0

    scores = [c.relevance_score for c in citations]
    count = len(scores)
    avg_score = statistics.mean(scores)

    # Count factor: saturates at 5 citations (more than 5 doesn't help much)
    max_useful_citations = 5
    count_factor = min(count / max_useful_citations, 1.0)

    # Consistency factor: low standard deviation means the sources agree
    if count > 1:
        spread = statistics.stdev(scores)
        # stdev of 0 -> consistency 1.0, stdev of 0.5+ -> consistency ~0.0
        consistency_factor = max(1.0 - (spread * 2.0), 0.0)
    else:
        # Single citation: neutral consistency (neither good nor bad)
        consistency_factor = 0.5

    # Weighted combination
    # Average score is the strongest signal (50%)
    # Count provides supporting evidence (30%)
    # Consistency is a secondary quality check (20%)
    confidence = 0.5 * avg_score + 0.3 * count_factor + 0.2 * consistency_factor

    # Clamp to [0.0, 1.0]
    return max(0.0, min(confidence, 1.0))


def should_abstain(confidence: float, threshold: float = 0.3) -> bool:
    """Return True if confidence is too low to provide a useful answer.

    When this returns True, the system should respond with an
    "I don't know" guardrail message instead of generating an answer.

    Args:
        confidence: The confidence score from ``calculate_confidence``.
        threshold: Minimum confidence required to generate an answer.
            Defaults to ``0.3``.

    Returns:
        ``True`` if the confidence is below the threshold, ``False``
        otherwise.
    """
    return confidence < threshold
