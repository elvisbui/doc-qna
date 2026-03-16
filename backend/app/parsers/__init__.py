"""Document parsers — dispatch to the correct parser based on file extension."""

from collections.abc import Callable
from pathlib import Path

from app.core.exceptions import UnsupportedFileTypeError
from app.parsers.docx import parse_docx
from app.parsers.markdown import parse_text
from app.parsers.pdf import parse_pdf, parse_pdf_with_pages

_PARSER_MAP: dict[str, Callable[[Path], str]] = {
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".md": parse_text,
    ".txt": parse_text,
}

# Single source of truth for supported file types
SUPPORTED_FILE_TYPES: frozenset[str] = frozenset(_PARSER_MAP.keys())


def parse_document(file_path: Path) -> str:
    """Parse a document file and return its text content.

    Dispatches to the correct parser based on the file extension.

    Args:
        file_path: Path to the document file.

    Returns:
        Extracted text content as a string.

    Raises:
        UnsupportedFileTypeError: If the file extension is not supported.
    """
    extension = file_path.suffix.lower()
    parser = _PARSER_MAP.get(extension)
    if parser is None:
        raise UnsupportedFileTypeError(extension)
    return parser(file_path)


def parse_document_with_pages(file_path: Path) -> list[tuple[int, str]]:
    """Parse a document and return page-annotated text.

    For PDFs, returns a list of (page_number, text) tuples with 1-indexed
    page numbers. For non-PDF formats (which have no concept of pages),
    returns [(1, full_text)].

    Args:
        file_path: Path to the document file.

    Returns:
        A list of (page_number, text) tuples.

    Raises:
        UnsupportedFileTypeError: If the file extension is not supported.
    """
    extension = file_path.suffix.lower()
    if extension not in _PARSER_MAP:
        raise UnsupportedFileTypeError(extension)

    if extension == ".pdf":
        return parse_pdf_with_pages(file_path)

    # Non-PDF formats: parse normally and wrap as page 1
    text = _PARSER_MAP[extension](file_path)
    return [(1, text)]
