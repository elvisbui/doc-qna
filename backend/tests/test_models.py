"""Tests for core domain models."""

from datetime import datetime
from uuid import UUID

from app.core.models import Citation, Document, DocumentChunk, DocumentStatus


class TestDocument:
    """Tests for the Document model."""

    def test_document_creation_with_defaults(self):
        doc = Document(filename="test.pdf", file_type=".pdf", file_size=1024)
        assert isinstance(doc.id, UUID)
        assert doc.filename == "test.pdf"
        assert doc.file_type == ".pdf"
        assert doc.file_size == 1024
        assert doc.status == DocumentStatus.pending
        assert isinstance(doc.created_at, datetime)
        assert doc.error_message is None

    def test_document_creation_with_explicit_values(self):
        doc = Document(
            filename="report.docx",
            file_type=".docx",
            file_size=2048,
            status=DocumentStatus.ready,
            error_message=None,
        )
        assert doc.status == DocumentStatus.ready

    def test_document_created_at_is_utc(self):
        doc = Document(filename="test.md", file_type=".md", file_size=512)
        assert doc.created_at.tzinfo is not None

    def test_each_document_gets_unique_id(self):
        doc1 = Document(filename="a.md", file_type=".md", file_size=100)
        doc2 = Document(filename="b.md", file_type=".md", file_size=100)
        assert doc1.id != doc2.id


class TestDocumentStatus:
    """Tests for the DocumentStatus enum."""

    def test_enum_values(self):
        assert DocumentStatus.pending == "pending"
        assert DocumentStatus.processing == "processing"
        assert DocumentStatus.ready == "ready"
        assert DocumentStatus.error == "error"

    def test_enum_is_string(self):
        # DocumentStatus inherits from str, so values are strings
        assert isinstance(DocumentStatus.pending, str)

    def test_all_statuses_exist(self):
        statuses = {s.value for s in DocumentStatus}
        assert statuses == {"pending", "processing", "ready", "error"}


class TestCitation:
    """Tests for the Citation model."""

    def test_citation_creation(self):
        from uuid import uuid4

        doc_id = uuid4()
        citation = Citation(
            document_id=doc_id,
            document_name="notes.md",
            chunk_content="Some relevant content",
            chunk_index=3,
            relevance_score=0.85,
        )
        assert citation.document_id == doc_id
        assert citation.document_name == "notes.md"
        assert citation.chunk_content == "Some relevant content"
        assert citation.chunk_index == 3
        assert citation.relevance_score == 0.85

    def test_citation_relevance_score_bounds(self):
        from uuid import uuid4

        # Pydantic doesn't enforce bounds on plain float fields in the domain model
        # (bounds are on the schema layer), so this just verifies it stores the value
        citation = Citation(
            document_id=uuid4(),
            document_name="test.md",
            chunk_content="content",
            chunk_index=0,
            relevance_score=0.0,
        )
        assert citation.relevance_score == 0.0


class TestDocumentChunk:
    """Tests for the DocumentChunk model."""

    def test_document_chunk_defaults(self):
        from uuid import uuid4

        doc_id = uuid4()
        chunk = DocumentChunk(
            document_id=doc_id,
            content="chunk text",
            chunk_index=0,
        )
        assert isinstance(chunk.id, UUID)
        assert chunk.document_id == doc_id
        assert chunk.content == "chunk text"
        assert chunk.chunk_index == 0
        assert chunk.metadata == {}

    def test_document_chunk_with_metadata(self):
        from uuid import uuid4

        chunk = DocumentChunk(
            document_id=uuid4(),
            content="content",
            chunk_index=1,
            metadata={"document_name": "test.pdf"},
        )
        assert chunk.metadata["document_name"] == "test.pdf"
