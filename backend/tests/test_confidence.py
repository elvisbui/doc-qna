"""Tests for the confidence scoring service."""

from uuid import uuid4

import pytest

from app.core.models import Citation
from app.services.confidence import calculate_confidence, should_abstain


def _make_citation(relevance_score: float) -> Citation:
    """Helper to create a Citation with a given relevance score."""
    return Citation(
        document_id=uuid4(),
        document_name="test.md",
        chunk_content="test content",
        chunk_index=0,
        relevance_score=relevance_score,
    )


class TestCalculateConfidence:
    """Tests for calculate_confidence."""

    def test_empty_citations_returns_zero(self):
        assert calculate_confidence([]) == 0.0

    def test_single_citation_produces_moderate_confidence(self):
        citations = [_make_citation(0.8)]
        confidence = calculate_confidence(citations)
        # Single citation: avg=0.8, count_factor=1/5=0.2, consistency=0.5
        # confidence = 0.5*0.8 + 0.3*0.2 + 0.2*0.5 = 0.4 + 0.06 + 0.1 = 0.56
        assert 0.3 < confidence < 0.8
        assert confidence == pytest.approx(0.56)

    def test_multiple_high_score_citations_produce_high_confidence(self):
        citations = [_make_citation(0.9) for _ in range(5)]
        confidence = calculate_confidence(citations)
        # 5 citations: avg=0.9, count_factor=1.0, consistency=1.0 (stdev=0)
        # confidence = 0.5*0.9 + 0.3*1.0 + 0.2*1.0 = 0.45 + 0.3 + 0.2 = 0.95
        assert confidence > 0.8
        assert confidence == pytest.approx(0.95)

    def test_low_score_citations_produce_low_confidence(self):
        citations = [_make_citation(0.1) for _ in range(2)]
        confidence = calculate_confidence(citations)
        # avg=0.1, count_factor=2/5=0.4, consistency=1.0 (stdev=0)
        # confidence = 0.5*0.1 + 0.3*0.4 + 0.2*1.0 = 0.05 + 0.12 + 0.2 = 0.37
        assert confidence < 0.5

    def test_confidence_is_clamped_between_zero_and_one(self):
        # Even with extreme inputs, result should be in [0, 1]
        high = calculate_confidence([_make_citation(1.0) for _ in range(10)])
        assert 0.0 <= high <= 1.0

        low = calculate_confidence([_make_citation(0.0)])
        assert 0.0 <= low <= 1.0

    def test_mixed_scores_reduce_consistency(self):
        # High spread should lower confidence compared to uniform scores
        uniform = calculate_confidence([_make_citation(0.7) for _ in range(3)])
        mixed = calculate_confidence([_make_citation(0.2), _make_citation(0.7), _make_citation(0.95)])
        # Mixed scores have higher stdev -> lower consistency factor
        assert mixed < uniform


class TestShouldAbstain:
    """Tests for should_abstain."""

    def test_should_abstain_true_for_low_confidence(self):
        assert should_abstain(0.1) is True
        assert should_abstain(0.0) is True
        assert should_abstain(0.29) is True

    def test_should_abstain_false_for_high_confidence(self):
        assert should_abstain(0.5) is False
        assert should_abstain(0.8) is False
        assert should_abstain(1.0) is False

    def test_should_abstain_at_threshold_returns_false(self):
        # Exactly at threshold (0.3): not strictly less than, so False
        assert should_abstain(0.3) is False

    def test_should_abstain_custom_threshold(self):
        assert should_abstain(0.5, threshold=0.6) is True
        assert should_abstain(0.7, threshold=0.6) is False
