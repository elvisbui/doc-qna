"""Ingestion service — parse, chunk, embed, and index documents."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from app.core.exceptions import DocumentProcessingError
from app.core.models import Document, DocumentChunk
from app.parsers import parse_document
from app.providers.embedder import get_embedding_provider
from app.services.chunking import chunk_text, semantic_chunk_text
from app.services.vectorstore import add_chunks, get_default_collection

if TYPE_CHECKING:
    from pathlib import Path

    from chromadb.api.models.Collection import Collection

    from app.config import Settings
    from app.providers.base import EmbeddingProvider


async def ingest_document(
    file_path: Path,
    document: Document,
    settings: Settings,
    collection: Collection | None = None,
    embedder: EmbeddingProvider | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    """Run the full ingestion pipeline for an uploaded document."""
    document_id = str(document.id)

    try:
        # 1. Parse document
        text = await asyncio.to_thread(parse_document, file_path)

        if not text or not text.strip():
            raise DocumentProcessingError(document_id, "Document contains no extractable text")

        # 2. Chunk the text
        if settings.CHUNKING_STRATEGY == "semantic":
            if chunk_size is not None:
                text_chunks = semantic_chunk_text(text, max_chunk_size=chunk_size)
            else:
                text_chunks = semantic_chunk_text(text)
        else:
            kwargs: dict[str, int] = {}
            if chunk_size is not None:
                kwargs["chunk_size"] = chunk_size
            if chunk_overlap is not None:
                kwargs["chunk_overlap"] = chunk_overlap
            text_chunks = chunk_text(text, **kwargs)

        if not text_chunks:
            raise DocumentProcessingError(document_id, "Document produced no text chunks")

        # 3. Create DocumentChunk objects
        chunk_metadata: dict[str, str] = {"document_name": document.filename}
        if document.user_id is not None:
            chunk_metadata["user_id"] = document.user_id

        chunks = [
            DocumentChunk(
                document_id=document.id,
                content=content,
                chunk_index=i,
                metadata=dict(chunk_metadata),
            )
            for i, content in enumerate(text_chunks)
        ]

        # 4. Embed all chunks
        if embedder is None:
            embedder = get_embedding_provider(settings)
        embeddings = await embedder.embed_batch([chunk.content for chunk in chunks])

        # 5. Store in ChromaDB
        if collection is None:
            collection = get_default_collection(settings)
        await asyncio.to_thread(add_chunks, collection, chunks, embeddings)

        return chunks

    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(document_id, str(exc)) from exc
