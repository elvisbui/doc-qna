"""PDF document parser using pypdf."""

from pathlib import Path

from pypdf import PdfReader


def parse_pdf_with_pages(file_path: Path) -> list[tuple[int, str]]:
    """Extract text from a PDF file, preserving page numbers.

    Args:
        file_path: Path to the PDF file.

    Returns:
        A list of (page_number, text) tuples with 1-indexed page numbers.
        Only pages with extractable text are included.
    """
    reader = PdfReader(file_path)
    result: list[tuple[int, str]] = []
    for page_num, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            result.append((page_num, text))
    return result


def parse_pdf(file_path: Path) -> str:
    """Extract all text from a PDF file.

    Args:
        file_path: Path to the PDF file.

    Returns:
        Concatenated text from all pages, separated by newlines.
    """
    pages = parse_pdf_with_pages(file_path)
    return "\n".join(text for _, text in pages)
