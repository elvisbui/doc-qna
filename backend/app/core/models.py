"""Domain models for the doc-qna application."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DocumentStatus(StrEnum):
    """Processing status of an uploaded document."""

    pending = "pending"
    processing = "processing"
    ready = "ready"
    error = "error"


class Document(BaseModel):
    """An uploaded document tracked by the system."""

    id: UUID = Field(default_factory=uuid4)
    filename: str
    file_type: str
    file_size: int
    status: DocumentStatus = DocumentStatus.pending
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    error_message: str | None = None
    user_id: str | None = None


class DocumentChunk(BaseModel):
    """A single chunk produced by splitting a document."""

    id: UUID = Field(default_factory=uuid4)
    document_id: UUID
    content: str
    chunk_index: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class Citation(BaseModel):
    """A source reference attached to an answer."""

    document_id: UUID
    document_name: str
    chunk_content: str
    chunk_index: int
    relevance_score: float
    page_number: int | None = None
