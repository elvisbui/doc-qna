"""Structured JSON error handling for the doc-qna application.

Registers exception handlers that return a consistent envelope:
    {"error": {"type": "...", "message": "...", "detail": ... | null}}
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    DocumentProcessingError,
    ProviderError,
    RetrievalError,
    UnsupportedFileTypeError,
)

logger = logging.getLogger(__name__)


def _error_response(status_code: int, error_type: str, message: str, detail: Any = None) -> JSONResponse:
    """Build a consistent JSON error response."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": error_type,
                "message": message,
                "detail": detail,
            }
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle FastAPI/Starlette HTTPException — preserve status code."""
    return _error_response(
        status_code=exc.status_code,
        error_type="http_error",
        message=str(exc.detail),
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle Pydantic / FastAPI request validation errors — 422 with field details."""
    field_errors = []
    for err in exc.errors():
        field_errors.append(
            {
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
        )
    return _error_response(
        status_code=422,
        error_type="validation_error",
        message="Request validation failed.",
        detail=field_errors,
    )


async def provider_error_handler(request: Request, exc: ProviderError) -> JSONResponse:
    """Handle LLM / embedder provider failures — 502 Bad Gateway."""
    logger.exception("Provider error: %s", exc)
    return _error_response(
        status_code=502,
        error_type="provider_error",
        message=f"Provider '{exc.provider}' encountered an error.",
        detail=exc.reason,
    )


async def retrieval_error_handler(request: Request, exc: RetrievalError) -> JSONResponse:
    """Handle vector search / retrieval failures — 500."""
    logger.exception("Retrieval error: %s", exc)
    return _error_response(
        status_code=500,
        error_type="retrieval_error",
        message="An error occurred during document retrieval.",
        detail=exc.reason,
    )


async def document_processing_error_handler(request: Request, exc: DocumentProcessingError) -> JSONResponse:
    """Handle document ingestion / processing failures — 422."""
    return _error_response(
        status_code=422,
        error_type="document_processing_error",
        message=str(exc),
        detail=exc.reason,
    )


async def unsupported_file_type_handler(request: Request, exc: UnsupportedFileTypeError) -> JSONResponse:
    """Handle unsupported file type uploads — 400."""
    return _error_response(
        status_code=400,
        error_type="unsupported_file_type",
        message=str(exc),
        detail=exc.file_type,
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — 500 with generic message."""
    logger.exception("Unhandled exception: %s", exc)
    return _error_response(
        status_code=500,
        error_type="internal_error",
        message="An unexpected error occurred. Please try again later.",
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI application."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ProviderError, provider_error_handler)
    app.add_exception_handler(RetrievalError, retrieval_error_handler)
    app.add_exception_handler(DocumentProcessingError, document_processing_error_handler)
    app.add_exception_handler(UnsupportedFileTypeError, unsupported_file_type_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
