"""Persistent document metadata store using SQLite.

Stores document records so they survive server restarts.
Follows the same aiosqlite pattern as metrics.py.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from uuid import UUID

import aiosqlite

from app.core.models import Document, DocumentStatus

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "documents.db")

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    file_type TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    error_message TEXT,
    user_id TEXT
)
"""

_initialized_dbs: set[str] = set()


@asynccontextmanager
async def _get_db(db_path: str | None = None) -> AsyncIterator[aiosqlite.Connection]:
    """Open a connection, ensure the table exists, and close on exit.

    Args:
        db_path: Optional path to the SQLite database file. Defaults to
            ``_DEFAULT_DB_PATH`` when ``None``.

    Yields:
        An open ``aiosqlite.Connection`` with row factory set to
        ``aiosqlite.Row``.
    """
    path = db_path or _DEFAULT_DB_PATH
    async with aiosqlite.connect(path) as db:
        if path not in _initialized_dbs:
            await db.execute(_CREATE_TABLE_SQL)
            await db.commit()
            _initialized_dbs.add(path)
        db.row_factory = aiosqlite.Row
        yield db


def _row_to_document(row: aiosqlite.Row) -> Document:
    """Convert a database row to a Document model.

    Args:
        row: A database row with columns matching the ``documents`` table schema.

    Returns:
        A ``Document`` instance populated from the row data.
    """
    return Document(
        id=UUID(row["id"]),
        filename=row["filename"],
        file_type=row["file_type"],
        file_size=row["file_size"],
        status=DocumentStatus(row["status"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        error_message=row["error_message"],
        user_id=row["user_id"],
    )


async def save_document(doc: Document, db_path: str | None = None) -> None:
    """Insert or replace a document record.

    If a document with the same ID already exists, it is replaced.

    Args:
        doc: The ``Document`` model to persist.
        db_path: Optional path to the SQLite database file.
    """
    async with _get_db(db_path) as db:
        await db.execute(
            """
            INSERT OR REPLACE INTO documents
                (id, filename, file_type, file_size, status, created_at, error_message, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(doc.id),
                doc.filename,
                doc.file_type,
                doc.file_size,
                doc.status.value,
                doc.created_at.isoformat(),
                doc.error_message,
                doc.user_id,
            ),
        )
        await db.commit()


async def update_document_status(
    document_id: str,
    status: DocumentStatus,
    error_message: str | None = None,
    db_path: str | None = None,
) -> None:
    """Update the status (and optional error message) of a document.

    Args:
        document_id: The UUID string of the document to update.
        status: The new ``DocumentStatus`` to set.
        error_message: Optional error message to store alongside
            a ``failed`` status.
        db_path: Optional path to the SQLite database file.
    """
    async with _get_db(db_path) as db:
        await db.execute(
            "UPDATE documents SET status = ?, error_message = ? WHERE id = ?",
            (status.value, error_message, document_id),
        )
        await db.commit()


async def get_document(document_id: str, db_path: str | None = None) -> Document | None:
    """Fetch a single document by ID.

    Args:
        document_id: The UUID string of the document to retrieve.
        db_path: Optional path to the SQLite database file.

    Returns:
        The ``Document`` if found, or ``None`` if no matching row exists.
    """
    async with _get_db(db_path) as db:
        cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (document_id,))
        row = await cursor.fetchone()
        if row is None:
            return None
        return _row_to_document(row)


async def list_documents(user_id: str | None = None, db_path: str | None = None) -> list[Document]:
    """List all documents, optionally filtered by user_id.

    Args:
        user_id: Optional user ID to filter documents by owner. When
            ``None``, all documents are returned.
        db_path: Optional path to the SQLite database file.

    Returns:
        A list of ``Document`` instances ordered by creation date descending.
    """
    async with _get_db(db_path) as db:
        if user_id is not None:
            cursor = await db.execute(
                "SELECT * FROM documents WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,),
            )
        else:
            cursor = await db.execute("SELECT * FROM documents ORDER BY created_at DESC")
        rows = await cursor.fetchall()
        return [_row_to_document(row) for row in rows]


async def delete_document(document_id: str, db_path: str | None = None) -> bool:
    """Delete a document by ID.

    Args:
        document_id: The UUID string of the document to delete.
        db_path: Optional path to the SQLite database file.

    Returns:
        ``True`` if a row was deleted, ``False`` if no matching row existed.
    """
    async with _get_db(db_path) as db:
        cursor = await db.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        await db.commit()
        return cursor.rowcount > 0
