"""Tests for page-number citation feature."""

import json
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.models import Citation
from app.services.generation import _serialize_citations

# Minimal valid 2-page PDF created with raw PDF syntax (no reportlab needed)
_TWO_PAGE_PDF = (
    b"%PDF-1.4\n"
    b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    b"2 0 obj\n<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>\nendobj\n"
    b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 5 0 R /Resources << /Font << /F1 7 0 R >> >> >>\nendobj\n"
    b"4 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
    b"/Contents 6 0 R /Resources << /Font << /F1 7 0 R >> >> >>\nendobj\n"
    b"5 0 obj\n<< /Length 44 >>\nstream\n"
    b"BT /F1 12 Tf 100 700 Td (Page one content) Tj ET\n"
    b"endstream\nendobj\n"
    b"6 0 obj\n<< /Length 44 >>\nstream\n"
    b"BT /F1 12 Tf 100 700 Td (Page two content) Tj ET\n"
    b"endstream\nendobj\n"
    b"7 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
    b"xref\n0 8\n"
    b"0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
    b"0000000115 00000 n \n0000000266 00000 n \n0000000417 00000 n \n"
    b"0000000512 00000 n \n0000000607 00000 n \n"
    b"trailer\n<< /Size 8 /Root 1 0 R >>\nstartxref\n688\n%%EOF"
)


def _write_test_pdf(path: Path) -> None:
    """Write the two-page test PDF to *path*."""
    path.write_bytes(_TWO_PAGE_PDF)


class TestParsePdfWithPages:
    """Tests for parse_pdf_with_pages."""

    def test_returns_page_numbers(self, tmp_path: Path):
        """Test that parse_pdf_with_pages returns 1-indexed page tuples."""
        from app.parsers.pdf import parse_pdf_with_pages

        pdf_path = tmp_path / "test.pdf"
        _write_test_pdf(pdf_path)

        result = parse_pdf_with_pages(pdf_path)

        assert len(result) == 2
        assert result[0][0] == 1  # first page number is 1
        assert result[1][0] == 2  # second page number is 2
        assert "Page one content" in result[0][1]
        assert "Page two content" in result[1][1]

    def test_backward_compatible_parse_pdf(self, tmp_path: Path):
        """Test that the original parse_pdf still returns a plain string."""
        from app.parsers.pdf import parse_pdf

        pdf_path = tmp_path / "test.pdf"
        _write_test_pdf(pdf_path)

        result = parse_pdf(pdf_path)

        assert isinstance(result, str)
        assert "Page one content" in result


class TestParseDocumentWithPages:
    """Tests for parse_document_with_pages."""

    def test_non_pdf_returns_page_one(self, tmp_path: Path):
        """Non-PDF formats should return [(1, full_text)]."""
        from app.parsers import parse_document_with_pages

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("Hello world", encoding="utf-8")

        result = parse_document_with_pages(txt_file)

        assert len(result) == 1
        assert result[0] == (1, "Hello world")

    def test_pdf_returns_page_tuples(self, tmp_path: Path):
        """PDF files should return per-page tuples."""
        from app.parsers import parse_document_with_pages

        pdf_path = tmp_path / "doc.pdf"
        _write_test_pdf(pdf_path)

        result = parse_document_with_pages(pdf_path)

        assert len(result) == 2
        assert result[0][0] == 1
        assert result[1][0] == 2


class TestCitationPageNumber:
    """Tests for the page_number field on Citation."""

    def test_citation_with_page_number(self):
        citation = Citation(
            document_id=uuid4(),
            document_name="report.pdf",
            chunk_content="Some content",
            chunk_index=0,
            relevance_score=0.9,
            page_number=5,
        )
        assert citation.page_number == 5

    def test_citation_without_page_number(self):
        citation = Citation(
            document_id=uuid4(),
            document_name="notes.md",
            chunk_content="Some content",
            chunk_index=0,
            relevance_score=0.8,
        )
        assert citation.page_number is None

    def test_citation_page_number_none_explicit(self):
        citation = Citation(
            document_id=uuid4(),
            document_name="test.txt",
            chunk_content="Content",
            chunk_index=0,
            relevance_score=0.7,
            page_number=None,
        )
        assert citation.page_number is None


class TestSerializeCitations:
    """Tests for _serialize_citations including pageNumber."""

    def test_serialization_includes_page_number(self):
        citation = Citation(
            document_id=uuid4(),
            document_name="report.pdf",
            chunk_content="Content",
            chunk_index=2,
            relevance_score=0.85,
            page_number=3,
        )
        result = json.loads(_serialize_citations([citation]))

        assert len(result) == 1
        assert result[0]["pageNumber"] == 3

    def test_serialization_page_number_null_when_none(self):
        citation = Citation(
            document_id=uuid4(),
            document_name="notes.md",
            chunk_content="Content",
            chunk_index=0,
            relevance_score=0.7,
        )
        result = json.loads(_serialize_citations([citation]))

        assert len(result) == 1
        assert result[0]["pageNumber"] is None


class TestIngestionPageNumber:
    """Tests that ingestion stores page_number in chunk metadata."""

    @pytest.mark.asyncio
    async def test_pdf_chunks_have_page_number(self, tmp_path: Path):
        """Chunks from PDF ingestion should have page_number in metadata."""
        from app.core.models import Document
        from app.services.ingestion import ingest_document

        pdf_path = tmp_path / "test.pdf"
        _write_test_pdf(pdf_path)

        document = Document(filename="test.pdf", file_type=".pdf", file_size=1000)

        # Mock settings, embedder, and collection
        mock_settings = MagicMock()
        mock_settings.CHUNKING_STRATEGY = "fixed"
        mock_embedder = MagicMock()

        async def mock_embed_batch(texts):
            return [[0.1] * 10 for _ in texts]

        mock_embedder.embed_batch = mock_embed_batch

        mock_collection = MagicMock()

        chunks = await ingest_document(
            file_path=pdf_path,
            document=document,
            settings=mock_settings,
            collection=mock_collection,
            embedder=mock_embedder,
            chunk_size=5000,  # Large chunk size to keep all text in one chunk
            chunk_overlap=0,
        )

        assert len(chunks) > 0
        # At least the first chunk should have a page_number
        assert "page_number" in chunks[0].metadata
        assert isinstance(chunks[0].metadata["page_number"], int)
        assert chunks[0].metadata["page_number"] >= 1
