"""API request/response schemas for document endpoints."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import to_camel


class DocumentUploadResponse(BaseModel):
    """Response returned after a document upload is accepted."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        json_schema_extra={
            "examples": [
                {
                    "documentId": "b5f7d3a0-1234-4abc-9def-0123456789ab",
                    "filename": "report.pdf",
                    "status": "pending",
                }
            ]
        },
    )

    document_id: UUID
    filename: str
    status: str = "pending"


class DocumentResponse(BaseModel):
    """Full document metadata returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        json_schema_extra={
            "examples": [
                {
                    "id": "b5f7d3a0-1234-4abc-9def-0123456789ab",
                    "filename": "report.pdf",
                    "fileType": ".pdf",
                    "fileSize": 204800,
                    "status": "ready",
                    "createdAt": "2026-01-15T10:30:00Z",
                    "errorMessage": None,
                }
            ]
        },
    )

    id: UUID
    filename: str
    file_type: str
    file_size: int = Field(..., description="File size in bytes")
    status: str
    created_at: datetime
    error_message: str | None = None


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    documents: list[DocumentResponse]
    total: int


class DocumentPreviewResponse(BaseModel):
    """Parsed text preview of a document."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        json_schema_extra={
            "examples": [
                {
                    "content": "Chapter 1: Introduction\n\nThis document describes...",
                    "truncated": True,
                    "totalLength": 12500,
                }
            ]
        },
    )

    content: str
    truncated: bool
    total_length: int = Field(..., description="Total character count of parsed text")
