"""Tests for the CLI `config` command."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def _isolate_overlay(tmp_path, monkeypatch):
    """Point the config overlay to a temp directory so tests don't interfere."""
    overlay_file = tmp_path / "settings.json"
    monkeypatch.setattr(
        "app.core.overlay.overlay_path",
        lambda: overlay_file,
    )
    monkeypatch.setattr(
        "app.cli._config_overlay_path",
        lambda: overlay_file,
    )
    yield overlay_file


def test_config_show_all(_isolate_overlay) -> None:
    """Running `config` with no subcommand shows a table of all settings."""
    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    # Should contain table header and known keys
    assert "LLM_PROVIDER" in result.output
    assert "OLLAMA_MODEL" in result.output
    assert "Key" in result.output
    assert "Value" in result.output
    assert "Source" in result.output


def test_config_get_valid_key() -> None:
    """Getting a valid key prints its value."""
    result = runner.invoke(app, ["config", "get", "LLM_PROVIDER"])
    assert result.exit_code == 0
    assert "LLM_PROVIDER" in result.output
    # Value depends on environment (.env may override the default)
    assert result.output.strip().startswith("LLM_PROVIDER =")


def test_config_get_case_insensitive() -> None:
    """Key lookup should be case-insensitive."""
    result = runner.invoke(app, ["config", "get", "llm_provider"])
    assert result.exit_code == 0
    assert "LLM_PROVIDER" in result.output


def test_config_get_invalid_key() -> None:
    """Getting an invalid key shows an error with available keys."""
    result = runner.invoke(app, ["config", "get", "NOT_A_REAL_KEY"])
    assert result.exit_code == 1
    assert "Unknown key" in result.output
    assert "Available keys" in result.output
    # Should list some real keys
    assert "LLM_PROVIDER" in result.output


def test_config_set_key(_isolate_overlay) -> None:
    """Setting a key persists the value to the overlay file."""
    overlay_file = _isolate_overlay
    result = runner.invoke(app, ["config", "set", "LLM_PROVIDER", "openai"])
    assert result.exit_code == 0
    assert "Set" in result.output
    assert "LLM_PROVIDER" in result.output
    assert "openai" in result.output

    # Verify the overlay file was written
    data = json.loads(overlay_file.read_text())
    assert data["llm_provider"] == "openai"


def test_config_set_invalid_key() -> None:
    """Setting an invalid key shows an error."""
    result = runner.invoke(app, ["config", "set", "BOGUS_KEY", "val"])
    assert result.exit_code == 1
    assert "Unknown key" in result.output
    assert "Available keys" in result.output


def test_config_masks_api_keys() -> None:
    """API key values should be masked in output."""
    with patch("app.config.get_settings") as mock_settings:
        from app.config import Settings

        s = Settings(OPENAI_API_KEY="sk-1234567890abcdef")
        mock_settings.return_value = s

        result = runner.invoke(app, ["config", "get", "OPENAI_API_KEY"])
        assert result.exit_code == 0
        # Should NOT show the full key
        assert "sk-1234567890abcdef" not in result.output
        # Should show last 4 chars
        assert "cdef" in result.output


def test_config_show_overlay_source(_isolate_overlay) -> None:
    """After setting a key, the table should show 'overlay' as source."""
    overlay_file = _isolate_overlay
    # Write overlay
    overlay_file.write_text(json.dumps({"llm_provider": "openai"}))

    result = runner.invoke(app, ["config"])
    assert result.exit_code == 0
    assert "overlay" in result.output
