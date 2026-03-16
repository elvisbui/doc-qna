"""Document router — upload, list, delete.

Thin HTTP layer: validation and response formatting only.
Business logic lives in services/.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, UploadFile, status

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

    from app.providers.base import EmbeddingProvider

from app.config import get_settings
from app.core.constants import MAX_FILE_SIZE, PREVIEW_MAX_CHARS
from app.core.models import Document, DocumentStatus
from app.parsers import SUPPORTED_FILE_TYPES, parse_document
from app.routers import ERROR_RESPONSE_BODY
from app.schemas.documents import (
    DocumentListResponse,
    DocumentPreviewResponse,
    DocumentResponse,
    DocumentUploadResponse,
)
from app.services.document_store import (
    delete_document as db_delete_document,
)
from app.services.document_store import (
    get_document as db_get_document,
)
from app.services.document_store import (
    list_documents as db_list_documents,
)
from app.services.document_store import (
    save_document as db_save_document,
)
from app.services.document_store import (
    update_document_status as db_update_status,
)
from app.services.ingestion import ingest_document
from app.services.vectorstore import delete_by_document_id, get_default_collection

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


async def _run_ingestion(
    document_id: str,
    file_path: Path,
    collection: Collection | None = None,
    embedder: EmbeddingProvider | None = None,
) -> None:
    """Run the ingestion pipeline as a background task.

    Parses, chunks, and embeds the uploaded document, then updates its
    status to ``ready`` on success or ``error`` on failure.

    Args:
        document_id: The UUID of the document to ingest.
        file_path: Path to the uploaded file on disk.
        collection: Optional ChromaDB collection; uses the default if
            ``None``.
        embedder: Optional embedding provider; uses the default if ``None``.
    """
    doc = await db_get_document(document_id)
    if doc is None:
        return

    await db_update_status(document_id, DocumentStatus.processing)
    settings = get_settings()

    # Read chunk params from overlay (if user configured them via settings API).
    from app.core.overlay import load_overlay as _load_overlay

    _overlay = _load_overlay()
    _chunk_size = _overlay.get("chunk_size")
    _chunk_overlap = _overlay.get("chunk_overlap")

    try:
        await ingest_document(
            file_path,
            doc,
            settings,
            collection=collection,
            embedder=embedder,
            chunk_size=_chunk_size,
            chunk_overlap=_chunk_overlap,
        )
            await db_update_status(document_id, DocumentStatus.ready)
        logger.info("Document %s ingested successfully", document_id)
    except Exception as exc:
        await db_update_status(document_id, DocumentStatus.error, error_message=str(exc))
        logger.error("Ingestion failed for document %s: %s", document_id, exc)


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload a document",
    description="Upload a file for ingestion. Supported types: PDF, DOCX, Markdown, TXT. "
    "The file is validated and saved, then ingestion runs asynchronously in the background.",
    responses={
        400: {"description": "Invalid filename or unsupported file type", **ERROR_RESPONSE_BODY},
        413: {"description": "File exceeds maximum allowed size", **ERROR_RESPONSE_BODY},
        422: {"description": "Request validation failed", **ERROR_RESPONSE_BODY},
    },
)
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    request: Request,
) -> DocumentUploadResponse:
    """Accept a file upload, validate, save, and kick off ingestion."""
    # Validate filename exists
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    # Validate file type
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED_FILE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {suffix}. Supported: {', '.join(sorted(SUPPORTED_FILE_TYPES))}",
        )

    # Read file content and validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB.",
        )

    # Resolve user namespace (None when multi-user is disabled)
    user_id = resolve_user_id(request, get_settings())

    # Sanitize the filename (strip path components, keep only the basename)
    safe_filename = Path(file.filename).name

    # Create Document record
    doc = Document(
        filename=safe_filename,
        file_type=suffix,
        file_size=len(content),
        user_id=user_id,
    )
    document_id = str(doc.id)

    # Save file to UPLOAD_DIR
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{document_id}{suffix}"
    file_path.write_bytes(content)

    # Persist document metadata to SQLite
    await db_save_document(doc)

    # Kick off ingestion in background (use singleton embedder if available)
    collection = getattr(request.app.state, "chroma_collection", None)
    embedder = getattr(request.app.state, "embedder", None)
    background_tasks.add_task(_run_ingestion, document_id, file_path, collection, embedder)

    return DocumentUploadResponse(
        document_id=doc.id,
        filename=doc.filename,
        status=doc.status.value,
    )


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all documents",
    description="Return metadata for every uploaded document, including processing status.",
)
async def list_documents(request: Request) -> DocumentListResponse:
    """List all documents (filtered by user when multi-user is enabled)."""
    user_id = resolve_user_id(request, get_settings())
    docs = await db_list_documents(user_id=user_id)
    response_docs = [
        DocumentResponse(
            id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status.value,
            created_at=doc.created_at,
            error_message=doc.error_message,
        )
        for doc in docs
    ]
    return DocumentListResponse(documents=response_docs, total=len(response_docs))


@router.get(
    "/{document_id}/preview",
    response_model=DocumentPreviewResponse,
    summary="Preview document text",
    description="Return the parsed text content of a document, truncated to the first 5 000 characters.",
    responses={
        404: {"description": "Document not found", **ERROR_RESPONSE_BODY},
        422: {"description": "Document could not be parsed", **ERROR_RESPONSE_BODY},
    },
)
async def preview_document(document_id: str, request: Request) -> DocumentPreviewResponse:
    """Return parsed text content of a document (truncated to first 5000 chars)."""
    user_id = resolve_user_id(request, get_settings())
    doc = await db_get_document(document_id)
    if doc is None or (user_id is not None and doc.user_id != user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)
    file_path = upload_dir / f"{document_id}{doc.file_type}"

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File not found on disk for document: {document_id}",
        )

    try:
        full_text = await asyncio.to_thread(parse_document, file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Failed to parse document: {exc}",
        ) from exc

    total_length = len(full_text)
    truncated = total_length > PREVIEW_MAX_CHARS
    content = full_text[:PREVIEW_MAX_CHARS] if truncated else full_text

    return DocumentPreviewResponse(
        content=content,
        truncated=truncated,
        total_length=total_length,
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
    description="Remove a document, its file on disk, and all associated chunks from the vector store.",
    responses={
        404: {"description": "Document not found", **ERROR_RESPONSE_BODY},
    },
)
async def delete_document(document_id: str, request: Request) -> None:
    """Delete a document, its file on disk, and its chunks from ChromaDB."""
    user_id = resolve_user_id(request, get_settings())
    doc = await db_get_document(document_id)
    if doc is None or (user_id is not None and doc.user_id != user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document not found: {document_id}",
        )

    if doc.status == DocumentStatus.processing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Document '{document_id}' is currently being processed. Try again later.",
        )

    settings = get_settings()

    # Delete file from disk
    upload_dir = Path(settings.UPLOAD_DIR)
    file_path = upload_dir / f"{document_id}{doc.file_type}"
    if file_path.exists():
        file_path.unlink()

    # Delete chunks from ChromaDB
    try:
        collection = getattr(request.app.state, "chroma_collection", None)
        if collection is None:
            collection = get_default_collection(settings)
        await asyncio.to_thread(delete_by_document_id, collection, document_id)
        except Exception as exc:
        logger.warning("Failed to delete chunks from ChromaDB for %s: %s", document_id, exc)

    # Remove from SQLite
    await db_delete_document(document_id)
