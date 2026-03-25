"""Tests for the CLI `pack` command group."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from typer.testing import CliRunner

from app.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# pack list
# ---------------------------------------------------------------------------


def test_pack_list_shows_table() -> None:
    """``pack list`` should display a table with pack information."""
    fake_index = [
        {
            "name": "python-docs",
            "version": "1.0.0",
            "description": "Python documentation",
            "doc_count": 5,
            "installed": True,
        },
        {
            "name": "rust-book",
            "version": "0.2.0",
            "description": "The Rust Book",
            "doc_count": 12,
            "installed": False,
        },
    ]

    with patch("app.packs.registry.PackRegistry") as MockRegistry:
        instance = MockRegistry.return_value
        instance.scan_local.return_value = []
        instance.get_index.return_value = fake_index

        result = runner.invoke(app, ["pack", "list"])

    assert result.exit_code == 0
    assert "python-docs" in result.output
    assert "rust-book" in result.output
    assert "1.0.0" in result.output


def test_pack_list_empty() -> None:
    """``pack list`` with no packs should print an informational message."""
    with patch("app.packs.registry.PackRegistry") as MockRegistry:
        instance = MockRegistry.return_value
        instance.scan_local.return_value = []
        instance.get_index.return_value = []

        result = runner.invoke(app, ["pack", "list"])

    assert result.exit_code == 0
    assert "No packs" in result.output or "no packs" in result.output.lower()


# ---------------------------------------------------------------------------
# pack install
# ---------------------------------------------------------------------------


def test_pack_install_success(tmp_path) -> None:
    """``pack install <path>`` should call install_pack and report success."""
    fake_pack = tmp_path / "my-pack.tar.gz"
    fake_pack.write_bytes(b"fake")

    fake_manifest = MagicMock()
    fake_manifest.name = "my-pack"
    fake_manifest.version = "1.0.0"

    with patch("app.packs.installer.install_pack", new_callable=AsyncMock, return_value=fake_manifest):
        result = runner.invoke(app, ["pack", "install", str(fake_pack)])

    assert result.exit_code == 0
    assert "my-pack" in result.output


def test_pack_install_file_not_found() -> None:
    """``pack install`` with a non-existent path should fail."""
    result = runner.invoke(app, ["pack", "install", "/nonexistent/pack.tar.gz"])
    assert result.exit_code == 1
    assert "not found" in result.output.lower() or "Error" in result.output


def test_pack_install_validation_error(tmp_path) -> None:
    """``pack install`` should report errors from install_pack."""
    fake_pack = tmp_path / "bad-pack.tar.gz"
    fake_pack.write_bytes(b"fake")

    with patch(
        "app.packs.installer.install_pack",
        new_callable=AsyncMock,
        side_effect=ValueError("Invalid pack: missing manifest"),
    ):
        result = runner.invoke(app, ["pack", "install", str(fake_pack)])

    assert result.exit_code == 1
    assert "Invalid pack" in result.output or "Error" in result.output


# ---------------------------------------------------------------------------
# pack remove
# ---------------------------------------------------------------------------


def test_pack_remove_success() -> None:
    """``pack remove <name>`` should call uninstall_pack and report success."""
    with patch("app.packs.installer.uninstall_pack", new_callable=AsyncMock):
        result = runner.invoke(app, ["pack", "remove", "my-pack"])

    assert result.exit_code == 0
    assert "my-pack" in result.output


def test_pack_remove_error() -> None:
    """``pack remove`` should report errors from uninstall_pack."""
    with patch(
        "app.packs.installer.uninstall_pack",
        new_callable=AsyncMock,
        side_effect=Exception("collection not found"),
    ):
        result = runner.invoke(app, ["pack", "remove", "bad-pack"])

    assert result.exit_code == 1
    assert "Error" in result.output
