"""Tests for the chunk_text function in the ingestion service."""

import pytest

from app.services.chunking import chunk_text


class TestChunkTextBasic:
    """Basic chunking behavior."""

    def test_basic_chunking_produces_expected_chunks(self):
        text = "a" * 100
        chunks = chunk_text(text, chunk_size=30, chunk_overlap=10)
        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= 30

    def test_all_content_is_covered(self):
        text = "abcdefghijklmnopqrstuvwxyz"
        chunks = chunk_text(text, chunk_size=10, chunk_overlap=0)
        assert "".join(chunks) == text


class TestChunkTextOverlap:
    """Overlap correctness."""

    def test_overlap_is_correct(self):
        text = "a" * 50
        chunk_size = 20
        chunk_overlap = 5
        chunks = chunk_text(text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        # With step = 20 - 5 = 15, chunks start at 0, 15, 30, 45
        # The overlap between consecutive chunks should be chunk_overlap characters
        for i in range(len(chunks) - 1):
            # Compute start positions
            start_current = i * (chunk_size - chunk_overlap)
            start_next = (i + 1) * (chunk_size - chunk_overlap)
            end_current = start_current + chunk_size
            overlap_len = end_current - start_next
            assert overlap_len == chunk_overlap

    def test_overlap_content_matches(self):
        text = "abcdefghijklmnopqrstuvwxyz0123456789"
        chunks = chunk_text(text, chunk_size=15, chunk_overlap=5)
        # The last 5 chars of chunk[i] should equal the first 5 chars of chunk[i+1]
        for i in range(len(chunks) - 1):
            assert chunks[i][-5:] == chunks[i + 1][:5]


class TestChunkTextEdgeCases:
    """Edge cases and error handling."""

    def test_empty_input_returns_empty_list(self):
        assert chunk_text("") == []

    def test_whitespace_only_input_returns_empty_list(self):
        assert chunk_text("   \n\t  ") == []

    def test_text_shorter_than_chunk_size_returns_single_chunk(self):
        text = "short text"
        chunks = chunk_text(text, chunk_size=1000, chunk_overlap=200)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_overlap_ge_chunk_size_raises_value_error(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_text("some text", chunk_size=10, chunk_overlap=10)

    def test_chunk_overlap_greater_than_chunk_size_raises_value_error(self):
        with pytest.raises(ValueError, match="chunk_overlap"):
            chunk_text("some text", chunk_size=10, chunk_overlap=15)

    def test_none_input_returns_empty_list(self):
        assert chunk_text(None) == []
