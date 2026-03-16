"""Markdown and plain text file parsers."""

from pathlib import Path


def parse_text(file_path: Path) -> str:
    """Read a text-based file (Markdown, plain text) as UTF-8.

    Args:
        file_path: Path to the file.

    Returns:
        Raw file contents as a string.
    """
    return file_path.read_text(encoding="utf-8")
