"""Tests for the CLI entrypoint."""

import re

from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_app_exists() -> None:
    """The Typer app object should be importable."""
    assert app is not None


def test_help_exits_zero() -> None:
    """Running --help should succeed."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "doc-qna" in result.output.lower() or "usage" in result.output.lower()


def test_expected_commands_registered() -> None:
    """All required subcommands should be present in --help output."""
    result = runner.invoke(app, ["--help"])
    expected = ["ingest", "query", "status", "config", "serve", "eval"]
    for cmd in expected:
        assert cmd in result.output, f"Command '{cmd}' missing from CLI help"


def test_status_command_runs_successfully() -> None:
    """The status command should run and display provider info."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0, f"status exited with {result.exit_code}"
    assert "Provider Config" in result.output


def test_serve_help() -> None:
    """The serve command should accept --host, --port, and --reload options."""
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    output = _strip_ansi(result.output)
    assert "--host" in output
    assert "--port" in output
    assert "--reload" in output
