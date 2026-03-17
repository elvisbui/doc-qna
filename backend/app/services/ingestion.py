"""Ingestion service — parse, chunk, embed, and index documents.

This module implements the full ingestion pipeline: given an uploaded file,
it extracts text, splits it into overlapping chunks, generates embeddings,
and stores everything in ChromaDB for later retrieval.
"""

from __future__ import annotations

import asyncio
from bisect import bisect_right
from typing import TYPE_CHECKING

from app.core.exceptions import DocumentProcessingError
from app.core.models import Document, DocumentChunk
from app.parsers import parse_document_with_pages
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
    """Run the full ingestion pipeline for an uploaded document.

    Steps:
        1. Parse the document to extract raw text.
        2. Chunk the text into overlapping segments.
        3. Create ``DocumentChunk`` objects for each segment.
        4. Embed all chunks in a single batch via the configured embedder.
        5. Store chunks and embeddings in ChromaDB.

    Args:
        file_path: Path to the uploaded file on disk.
        document: The ``Document`` domain model for this upload.
        settings: Application settings (used for API keys and ChromaDB config).
        collection: Optional ChromaDB collection override.
        embedder: Optional singleton embedding provider (from app.state).

    Returns:
        A list of ``DocumentChunk`` objects that were created and indexed.

    Raises:
        DocumentProcessingError: If any step in the pipeline fails.
    """
    document_id = str(document.id)

    try:
        # 1. Parse document with page info (single parse pass)
        pages_with_numbers = await asyncio.to_thread(parse_document_with_pages, file_path)
        text = "\n".join(page_text for _, page_text in pages_with_numbers)

        if not text or not text.strip():
            raise DocumentProcessingError(document_id, "Document contains no extractable text")

        # 2. Chunk the text (using configured strategy)
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

        # 2b. Build page boundary map for offset → page_number lookup.
        # page_offsets[i] is the char offset where the i-th page starts in `text`.
        # page_numbers[i] is the corresponding 1-indexed page number.
        page_offsets: list[int] = []
        page_numbers: list[int] = []
        sep = "\n"
        cumulative_offset = 0
        for page_num, page_text in pages_with_numbers:
            page_offsets.append(cumulative_offset)
            page_numbers.append(page_num)
            cumulative_offset += len(page_text) + len(sep)

        def _page_at_offset(offset: int) -> int | None:
            """Return the page number for a character offset using binary search."""
            if not page_offsets:
                return None
            idx = bisect_right(page_offsets, offset) - 1
            return page_numbers[idx] if idx >= 0 else None

        # 3. Create DocumentChunk objects.
        # Track a running offset so each chunk maps to the correct page even
        # when duplicate text exists across pages.
        chunk_metadata_base: dict[str, str] = {"document_name": document.filename}
        if document.user_id is not None:
            chunk_metadata_base["user_id"] = document.user_id

        chunks = []
        search_start = 0
        for i, content in enumerate(text_chunks):
            meta: dict[str, str | int] = dict(chunk_metadata_base)
            pos = text.find(content, search_start)
            if pos != -1:
                page_num = _page_at_offset(pos)
                if page_num is not None:
                    meta["page_number"] = page_num
                search_start = pos + 1
            chunks.append(
                DocumentChunk(
                    document_id=document.id,
                    content=content,
                    chunk_index=i,
                    metadata=meta,
                )
            )

        # 4. Embed all chunks (use singleton embedder if provided)
        if embedder is None:
            embedder = get_embedding_provider(settings)
        embeddings = await embedder.embed_batch([chunk.content for chunk in chunks])

        # 5. Store in ChromaDB (sync calls wrapped with asyncio.to_thread)
        if collection is None:
            collection = get_default_collection(settings)
        await asyncio.to_thread(add_chunks, collection, chunks, embeddings)

        return chunks

    except DocumentProcessingError:
        raise
    except Exception as exc:
        raise DocumentProcessingError(document_id, str(exc)) from exc
