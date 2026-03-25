"""Tests for the CLI query command."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

from typer.testing import CliRunner

from app.cli import app
from app.core.models import Citation

runner = CliRunner()


def _make_citations(n: int = 2) -> list[Citation]:
    """Create a list of fake Citation objects."""
    return [
        Citation(
            document_id=uuid4(),
            document_name=f"doc_{i}.pdf",
            chunk_content=f"Chunk content {i}",
            chunk_index=i,
            relevance_score=0.9 - i * 0.1,
        )
        for i in range(n)
    ]


@patch("app.services.retrieval.retrieve_relevant_chunks", new_callable=AsyncMock)
@patch("app.services.confidence.calculate_confidence")
@patch("app.services.confidence.should_abstain", return_value=False)
@patch("app.services.generation.get_llm_provider")
@patch("app.config.get_settings")
def test_successful_query(
    mock_settings,
    mock_get_provider,
    mock_should_abstain,
    mock_calc_conf,
    mock_retrieve,
) -> None:
    """A successful query prints the answer, citations table, and confidence."""
    citations = _make_citations(2)
    mock_retrieve.return_value = citations
    mock_calc_conf.return_value = 0.85

    # Simulate a streaming provider
    async def fake_stream(query, context, **kwargs):
        for tok in ["Machine ", "learning ", "is..."]:
            yield tok

    provider = mock_get_provider.return_value
    provider.generate_stream = fake_stream

    result = runner.invoke(app, ["query", "What is machine learning?"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "Machine learning is..." in result.output
    assert "doc_0.pdf" in result.output
    assert "doc_1.pdf" in result.output
    assert "0.85" in result.output


@patch("app.services.retrieval.retrieve_relevant_chunks", new_callable=AsyncMock)
@patch("app.services.confidence.calculate_confidence")
@patch("app.services.confidence.should_abstain", return_value=True)
@patch("app.config.get_settings")
def test_abstain_on_low_confidence(
    mock_settings,
    mock_should_abstain,
    mock_calc_conf,
    mock_retrieve,
) -> None:
    """When confidence is low, the abstain message should be printed."""
    mock_retrieve.return_value = []
    mock_calc_conf.return_value = 0.1

    result = runner.invoke(app, ["query", "Something obscure?"])

    assert result.exit_code == 0, f"Unexpected exit: {result.output}"
    assert "don't have enough information" in result.output
    assert "0.10" in result.output


def test_empty_query_error() -> None:
    """An empty question string should cause an error exit."""
    result = runner.invoke(app, ["query", "   "])

    assert result.exit_code == 1
    assert "empty" in result.output.lower()
