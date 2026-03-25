"""Tests for the CLI `status` command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


def test_status_exits_zero() -> None:
    """The status command should exit with code 0."""
    with patch("app.services.vectorstore.get_chroma_client") as mock_client:
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0, f"Exit code {result.exit_code}: {result.output}"


def test_status_shows_provider_config() -> None:
    """The status output should include the Provider Config section."""
    with patch("app.services.vectorstore.get_chroma_client") as mock_client:
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        result = runner.invoke(app, ["status"])
        assert "Provider Config" in result.output
        assert "LLM Provider" in result.output
        assert "Embedding Provider" in result.output


def test_status_shows_chromadb_stats() -> None:
    """The status output should include the ChromaDB Stats section."""
    with patch("app.services.vectorstore.get_chroma_client") as mock_client:
        mock_collection = MagicMock()
        mock_collection.count.return_value = 42
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        result = runner.invoke(app, ["status"])
        assert "ChromaDB Stats" in result.output
        assert "Total Chunks" in result.output
        assert "42" in result.output


def test_status_shows_upload_directory() -> None:
    """The status output should include the Upload Directory section."""
    with patch("app.services.vectorstore.get_chroma_client") as mock_client:
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.return_value.get_or_create_collection.return_value = mock_collection

        result = runner.invoke(app, ["status"])
        assert "Upload Directory" in result.output


def test_status_handles_chromadb_error() -> None:
    """Status should handle ChromaDB errors gracefully."""
    with patch("app.services.vectorstore.get_chroma_client") as mock_client:
        mock_client.side_effect = RuntimeError("connection refused")

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "Error" in result.output or "error" in result.output
