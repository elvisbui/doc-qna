"""Tests for document parsers."""

from pathlib import Path

import pytest

from app.core.exceptions import UnsupportedFileTypeError
from app.parsers import parse_document
from app.parsers.markdown import parse_text


class TestParseMarkdown:
    """Tests for parse_text."""

    def test_parse_text_reads_file(self, tmp_path: Path):
        md_file = tmp_path / "test.md"
        content = "# Hello\n\nThis is a **markdown** file."
        md_file.write_text(content, encoding="utf-8")

        result = parse_text(md_file)
        assert result == content

    def test_parse_text_preserves_formatting(self, tmp_path: Path):
        md_file = tmp_path / "formatted.md"
        content = "- item 1\n- item 2\n\n```python\nprint('hello')\n```"
        md_file.write_text(content, encoding="utf-8")

        result = parse_text(md_file)
        assert "```python" in result
        assert "- item 1" in result


class TestParseText:
    """Tests for parse_text."""

    def test_parse_text_reads_file(self, tmp_path: Path):
        txt_file = tmp_path / "test.txt"
        content = "This is plain text content.\nWith multiple lines."
        txt_file.write_text(content, encoding="utf-8")

        result = parse_text(txt_file)
        assert result == content

    def test_parse_text_empty_file(self, tmp_path: Path):
        txt_file = tmp_path / "empty.txt"
        txt_file.write_text("", encoding="utf-8")

        result = parse_text(txt_file)
        assert result == ""


class TestParseDocument:
    """Tests for the parse_document dispatcher."""

    def test_dispatches_to_markdown_parser(self, tmp_path: Path):
        md_file = tmp_path / "doc.md"
        content = "# Markdown content"
        md_file.write_text(content, encoding="utf-8")

        result = parse_document(md_file)
        assert result == content

    def test_dispatches_to_text_parser(self, tmp_path: Path):
        txt_file = tmp_path / "doc.txt"
        content = "Plain text content"
        txt_file.write_text(content, encoding="utf-8")

        result = parse_document(txt_file)
        assert result == content

    def test_unsupported_file_type_raises_error(self, tmp_path: Path):
        bad_file = tmp_path / "doc.xyz"
        bad_file.write_text("content", encoding="utf-8")

        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            parse_document(bad_file)
        assert ".xyz" in str(exc_info.value)
        assert exc_info.value.file_type == ".xyz"

    def test_case_insensitive_extension(self, tmp_path: Path):
        md_file = tmp_path / "doc.MD"
        content = "# Uppercase extension"
        md_file.write_text(content, encoding="utf-8")

        # parse_document lowercases the extension
        result = parse_document(md_file)
        assert result == content
