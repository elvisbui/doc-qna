"""Tests for the CLI `serve` command."""

import re
from unittest.mock import patch

from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def test_serve_help_exits_zero() -> None:
    """Running `serve --help` should succeed."""
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0


def test_serve_help_shows_host_option() -> None:
    """`serve --help` should document the --host option."""
    result = runner.invoke(app, ["serve", "--help"])
    assert "--host" in _strip_ansi(result.output)


def test_serve_help_shows_port_option() -> None:
    """`serve --help` should document the --port option."""
    result = runner.invoke(app, ["serve", "--help"])
    assert "--port" in _strip_ansi(result.output)


def test_serve_help_shows_reload_option() -> None:
    """`serve --help` should document the --reload option."""
    result = runner.invoke(app, ["serve", "--help"])
    assert "--reload" in _strip_ansi(result.output)


def test_serve_help_shows_workers_option() -> None:
    """`serve --help` should document the --workers option."""
    result = runner.invoke(app, ["serve", "--help"])
    assert "--workers" in _strip_ansi(result.output)


def test_serve_help_shows_log_level_option() -> None:
    """`serve --help` should document the --log-level option."""
    result = runner.invoke(app, ["serve", "--help"])
    assert "--log-level" in _strip_ansi(result.output)


def test_serve_calls_uvicorn_with_defaults() -> None:
    """serve with no args should call uvicorn.run with expected defaults."""
    with patch("uvicorn.run") as mock_run:
        result = runner.invoke(app, ["serve"])
        assert result.exit_code == 0
        mock_run.assert_called_once()
        kwargs = mock_run.call_args
        assert kwargs[1]["host"] == "0.0.0.0" or kwargs.kwargs["host"] == "0.0.0.0"


def test_serve_passes_custom_options() -> None:
    """serve should forward CLI options to uvicorn.run."""
    with patch("uvicorn.run") as mock_run:
        result = runner.invoke(
            app,
            [
                "serve",
                "--host",
                "127.0.0.1",
                "--port",
                "9000",
                "--reload",
                "--workers",
                "4",
                "--log-level",
                "debug",
            ],
        )
        assert result.exit_code == 0
        mock_run.assert_called_once_with(
            "app.main:app",
            host="127.0.0.1",
            port=9000,
            reload=True,
            workers=4,
            log_level="debug",
        )


def test_serve_prints_banner() -> None:
    """serve should print a Rich banner with server info."""
    with patch("uvicorn.run"):
        result = runner.invoke(app, ["serve", "--host", "127.0.0.1", "--port", "3000"])
        assert "Doc Q&A Server" in result.output
        assert "127.0.0.1" in result.output
        assert "3000" in result.output
