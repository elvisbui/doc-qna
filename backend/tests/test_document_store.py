"""Tests for the SQLite document store."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.models import Document, DocumentStatus
from app.services.document_store import (
    _initialized_dbs,
    delete_document,
    get_document,
    list_documents,
    save_document,
    update_document_status,
)


@pytest.fixture()
def db_path(tmp_path: Path) -> str:
    """Return a temporary database path for each test."""
    path = str(tmp_path / "test_documents.db")
    _initialized_dbs.discard(path)
    return path


@pytest.fixture()
def sample_doc() -> Document:
    return Document(
        filename="test.md",
        file_type=".md",
        file_size=1234,
    )


class TestSaveAndGet:
    @pytest.mark.asyncio
    async def test_save_and_retrieve(self, db_path: str, sample_doc: Document) -> None:
        await save_document(sample_doc, db_path=db_path)
        retrieved = await get_document(str(sample_doc.id), db_path=db_path)

        assert retrieved is not None
        assert retrieved.id == sample_doc.id
        assert retrieved.filename == "test.md"
        assert retrieved.file_type == ".md"
        assert retrieved.file_size == 1234
        assert retrieved.status == DocumentStatus.pending

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, db_path: str) -> None:
        result = await get_document("nonexistent-id", db_path=db_path)
        assert result is None

    @pytest.mark.asyncio
    async def test_save_overwrites(self, db_path: str, sample_doc: Document) -> None:
        await save_document(sample_doc, db_path=db_path)
        sample_doc.filename = "updated.md"
        await save_document(sample_doc, db_path=db_path)

        retrieved = await get_document(str(sample_doc.id), db_path=db_path)
        assert retrieved is not None
        assert retrieved.filename == "updated.md"


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_update_to_ready(self, db_path: str, sample_doc: Document) -> None:
        await save_document(sample_doc, db_path=db_path)
        await update_document_status(str(sample_doc.id), DocumentStatus.ready, db_path=db_path)

        retrieved = await get_document(str(sample_doc.id), db_path=db_path)
        assert retrieved is not None
        assert retrieved.status == DocumentStatus.ready

    @pytest.mark.asyncio
    async def test_update_to_error_with_message(self, db_path: str, sample_doc: Document) -> None:
        await save_document(sample_doc, db_path=db_path)
        await update_document_status(
            str(sample_doc.id),
            DocumentStatus.error,
            error_message="Parse failed",
            db_path=db_path,
        )

        retrieved = await get_document(str(sample_doc.id), db_path=db_path)
        assert retrieved is not None
        assert retrieved.status == DocumentStatus.error
        assert retrieved.error_message == "Parse failed"


class TestListDocuments:
    @pytest.mark.asyncio
    async def test_list_empty(self, db_path: str) -> None:
        docs = await list_documents(db_path=db_path)
        assert docs == []

    @pytest.mark.asyncio
    async def test_list_multiple(self, db_path: str) -> None:
        doc1 = Document(filename="a.md", file_type=".md", file_size=100)
        doc2 = Document(filename="b.pdf", file_type=".pdf", file_size=200)
        await save_document(doc1, db_path=db_path)
        await save_document(doc2, db_path=db_path)

        docs = await list_documents(db_path=db_path)
        assert len(docs) == 2
        filenames = {d.filename for d in docs}
        assert filenames == {"a.md", "b.pdf"}

    @pytest.mark.asyncio
    async def test_list_filtered_by_user(self, db_path: str) -> None:
        doc1 = Document(filename="a.md", file_type=".md", file_size=100, user_id="alice")
        doc2 = Document(filename="b.md", file_type=".md", file_size=200, user_id="bob")
        await save_document(doc1, db_path=db_path)
        await save_document(doc2, db_path=db_path)

        alice_docs = await list_documents(user_id="alice", db_path=db_path)
        assert len(alice_docs) == 1
        assert alice_docs[0].filename == "a.md"


class TestDeleteDocument:
    @pytest.mark.asyncio
    async def test_delete_existing(self, db_path: str, sample_doc: Document) -> None:
        await save_document(sample_doc, db_path=db_path)
        result = await delete_document(str(sample_doc.id), db_path=db_path)

        assert result is True
        assert await get_document(str(sample_doc.id), db_path=db_path) is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, db_path: str) -> None:
        result = await delete_document("nonexistent", db_path=db_path)
        assert result is False


class TestPersistence:
    @pytest.mark.asyncio
    async def test_data_survives_reconnection(self, db_path: str, sample_doc: Document) -> None:
        """Documents persist across separate connections (simulates server restart)."""
        await save_document(sample_doc, db_path=db_path)

        # Clear init cache to force table re-check on next connection
        _initialized_dbs.discard(db_path)

        retrieved = await get_document(str(sample_doc.id), db_path=db_path)
        assert retrieved is not None
        assert retrieved.filename == sample_doc.filename
        assert retrieved.status == sample_doc.status
