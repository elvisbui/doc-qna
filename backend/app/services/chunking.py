"""Chunking strategies for document text.

Provides both fixed sliding-window chunking and semantic paragraph-based
chunking. The strategy is selected via the ``CHUNKING_STRATEGY`` setting.
"""

from __future__ import annotations

import re

from app.core.constants import CHUNK_OVERLAP, CHUNK_SIZE


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks using a sliding window.

    Args:
        text: The full document text to split.
        chunk_size: Maximum number of characters per chunk.
        chunk_overlap: Number of overlapping characters between consecutive chunks.

    Returns:
        A list of text chunks. Returns an empty list if the input text
        is empty or contains only whitespace.
    """
    if not text or not text.strip():
        return []

    if chunk_overlap >= chunk_size:
        raise ValueError(f"chunk_overlap ({chunk_overlap}) must be less than chunk_size ({chunk_size})")

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - chunk_overlap

    return chunks  # guaranteed non-empty if text is non-empty


def semantic_chunk_text(
    text: str,
    max_chunk_size: int = CHUNK_SIZE,
) -> list[str]:
    """Split text into chunks based on paragraph (topic) boundaries.

    The algorithm:
        1. Split text into paragraphs on double newlines.
        2. Group consecutive paragraphs together as long as the combined
           length does not exceed ``max_chunk_size``.
        3. When adding a paragraph would exceed the limit, start a new chunk.
        4. If a single paragraph exceeds ``max_chunk_size``, fall back to the
           fixed sliding-window chunker for that paragraph.

    Args:
        text: The full document text to split.
        max_chunk_size: Maximum number of characters per chunk.

    Returns:
        A list of text chunks. Returns an empty list if the input text
        is empty or contains only whitespace.
    """
    if not text or not text.strip():
        return []

    # Split on double newlines (one or more blank lines).
    paragraphs = re.split(r"\n\s*\n", text)

    # Filter out empty/whitespace-only paragraphs and strip each one.
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    if not paragraphs:
        return []

    chunks: list[str] = []
    current_group: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        # Length of what the group would become if we add this paragraph.
        # Account for the double-newline separator between paragraphs.
        separator_len = len("\n\n") if current_group else 0
        new_length = current_length + separator_len + len(paragraph)

        if new_length <= max_chunk_size:
            current_group.append(paragraph)
            current_length = new_length
        else:
            # Flush current group if non-empty.
            if current_group:
                chunks.append("\n\n".join(current_group))
                current_group = []
                current_length = 0

            # If this single paragraph exceeds max_chunk_size,
            # fall back to the fixed sliding-window chunker.
            if len(paragraph) > max_chunk_size:
                safe_overlap = min(CHUNK_OVERLAP, max_chunk_size - 1)
                sub_chunks = chunk_text(
                    paragraph,
                    chunk_size=max_chunk_size,
                    chunk_overlap=safe_overlap,
                )
                chunks.extend(sub_chunks)
            else:
                current_group = [paragraph]
                current_length = len(paragraph)

    # Flush any remaining paragraphs.
    if current_group:
        chunks.append("\n\n".join(current_group))

    return chunks  # guaranteed non-empty if text is non-empty
