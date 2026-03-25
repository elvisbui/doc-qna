"""Tests for the CLI `ingest` command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

from typer.testing import CliRunner

from app.cli import app
from app.core.models import DocumentChunk

runner = CliRunner()


def _make_fake_chunks(n: int = 3) -> list[DocumentChunk]:
    """Return a list of *n* fake DocumentChunk objects."""
    from uuid import uuid4

    doc_id = uuid4()
    return [DocumentChunk(document_id=doc_id, content=f"chunk {i}", chunk_index=i) for i in range(n)]


# --------------------------------------------------------------------------
# Successful ingestion of a .txt file
# --------------------------------------------------------------------------
@patch("app.services.ingestion.ingest_document", new_callable=AsyncMock)
def test_ingest_txt_file(mock_ingest: AsyncMock, tmp_path: Path) -> None:
    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Hello world, this is a test document.")

    fake_chunks = _make_fake_chunks(3)
    mock_ingest.return_value = fake_chunks

    result = runner.invoke(app, ["ingest", str(txt_file)])

    assert result.exit_code == 0, result.output
    assert "3" in result.output  # chunk count appears in summary
    assert "Ingestion complete" in result.output
    mock_ingest.assert_called_once()


# --------------------------------------------------------------------------
# Unsupported file type
# --------------------------------------------------------------------------
def test_ingest_unsupported_file_type(tmp_path: Path) -> None:
    bad_file = tmp_path / "image.png"
    bad_file.write_bytes(b"\x89PNG")

    result = runner.invoke(app, ["ingest", str(bad_file)])

    assert result.exit_code == 1
    assert "Unsupported file type" in result.output


# --------------------------------------------------------------------------
# Missing file
# --------------------------------------------------------------------------
def test_ingest_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent.txt"

    result = runner.invoke(app, ["ingest", str(missing)])

    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "Path not found" in result.output


# --------------------------------------------------------------------------
# Directory ingestion
# --------------------------------------------------------------------------
@patch("app.services.ingestion.ingest_document", new_callable=AsyncMock)
def test_ingest_directory(mock_ingest: AsyncMock, tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("File A content")
    (tmp_path / "b.md").write_text("# File B")
    (tmp_path / "skip.png").write_bytes(b"\x89PNG")

    mock_ingest.return_value = _make_fake_chunks(2)

    result = runner.invoke(app, ["ingest", str(tmp_path)])

    assert result.exit_code == 0, result.output
    # Two supported files should have been processed
    assert mock_ingest.call_count == 2
    assert "Ingestion complete" in result.output


# --------------------------------------------------------------------------
# Directory with no supported files
# --------------------------------------------------------------------------
def test_ingest_empty_directory(tmp_path: Path) -> None:
    (tmp_path / "photo.jpg").write_bytes(b"\xff\xd8")

    result = runner.invoke(app, ["ingest", str(tmp_path)])

    assert result.exit_code == 1
    assert "No supported files" in result.output
