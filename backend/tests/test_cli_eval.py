"""Tests for the CLI eval command."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
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
            chunk_content=f"Machine learning is a subset of AI chunk {i}",
            chunk_index=i,
            relevance_score=0.9 - i * 0.1,
        )
        for i in range(n)
    ]


def _write_test_set(cases: list[dict]) -> Path:
    """Write test cases to a temporary JSON file and return its path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(cases, tmp)
    tmp.close()
    return Path(tmp.name)


TEST_CASES = [
    {"query": "What is ML?", "expected_answer": "Machine learning is..."},
    {"query": "What is RAG?", "expected_answer": "Retrieval augmented generation..."},
]


@patch("app.services.retrieval.retrieve_relevant_chunks", new_callable=AsyncMock)
@patch("app.services.generation.get_llm_provider")
@patch("app.config.get_settings")
def test_valid_test_set_runs(mock_settings, mock_get_provider, mock_retrieve) -> None:
    """A valid test set should produce a results table and summary."""
    citations = _make_citations(2)
    mock_retrieve.return_value = citations

    async def fake_stream(query, context, **kwargs):
        for tok in ["Machine ", "learning ", "is ", "a ", "subset"]:
            yield tok

    provider = mock_get_provider.return_value
    provider.generate_stream = fake_stream

    test_file = _write_test_set(TEST_CASES)
    try:
        result = runner.invoke(app, ["eval", str(test_file)])
        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        # Should contain the results table
        assert "Evaluation Results" in result.output
        # Should contain summary
        assert "Summary" in result.output
        assert "Total test cases" in result.output
        # Should show both queries were evaluated
        assert "What is ML?" in result.output
        assert "What is RAG?" in result.output
    finally:
        test_file.unlink(missing_ok=True)


def test_missing_file_error() -> None:
    """A missing test set file should cause an error exit."""
    result = runner.invoke(app, ["eval", "/nonexistent/path/test_set.json"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower()


@patch("app.services.retrieval.retrieve_relevant_chunks", new_callable=AsyncMock)
@patch("app.services.generation.get_llm_provider")
@patch("app.config.get_settings")
def test_output_flag_saves_json(mock_settings, mock_get_provider, mock_retrieve) -> None:
    """The --output flag should save results to a JSON file."""
    citations = _make_citations(1)
    mock_retrieve.return_value = citations

    async def fake_stream(query, context, **kwargs):
        yield "Answer text"

    provider = mock_get_provider.return_value
    provider.generate_stream = fake_stream

    test_file = _write_test_set(TEST_CASES)
    output_file = Path(tempfile.mktemp(suffix=".json"))
    try:
        result = runner.invoke(app, ["eval", str(test_file), "--output", str(output_file)])
        assert result.exit_code == 0, f"Unexpected exit: {result.output}"
        assert output_file.exists(), "Output file should have been created"

        data = json.loads(output_file.read_text(encoding="utf-8"))
        assert "results" in data
        assert "summary" in data
        assert len(data["results"]) == len(TEST_CASES)
        assert data["summary"]["count"] == len(TEST_CASES)
    finally:
        test_file.unlink(missing_ok=True)
        output_file.unlink(missing_ok=True)
