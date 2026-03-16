"""Embedding cache — LRU cache for query embeddings.

Caches query embeddings to avoid redundant API calls for repeated queries.
Only query embeddings are cached (not document embeddings, which are one-time
during ingestion).
"""

from __future__ import annotations

import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """Simple LRU cache for embedding vectors keyed by text.

    Uses an ``OrderedDict`` to maintain insertion/access order.
    When the cache exceeds ``max_size``, the least recently used
    entry is evicted.

    Args:
        max_size: Maximum number of entries to store. Defaults to 128.
    """

    def __init__(self, max_size: int = 128) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, text: str) -> list[float] | None:
        """Look up a cached embedding by text.

        Moves the entry to the end (most recently used) on hit.

        Args:
            text: The text whose embedding to look up.

        Returns:
            The cached embedding vector, or ``None`` on cache miss.
        """
        if text in self._cache:
            self._hits += 1
            self._cache.move_to_end(text)
            return self._cache[text]
        self._misses += 1
        return None

    def put(self, text: str, embedding: list[float]) -> None:
        """Store an embedding in the cache.

        If the cache is full, the least recently used entry is evicted.

        Args:
            text: The text that was embedded.
            embedding: The embedding vector to cache.
        """
        if text in self._cache:
            self._cache.move_to_end(text)
            self._cache[text] = embedding
            return

        if len(self._cache) >= self._max_size:
            evicted_key, _ = self._cache.popitem(last=False)
            logger.debug("Embedding cache evicted entry for: %.50s...", evicted_key)

        self._cache[text] = embedding

    def clear(self) -> None:
        """Clear all cached entries and reset hit/miss statistics to zero."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        """Return the current number of cached entries.

        Returns:
            The number of embedding vectors currently stored in the cache.
        """
        return len(self._cache)

    @property
    def stats(self) -> dict[str, int]:
        """Return cache hit/miss statistics.

        Returns:
            A dict with keys ``size``, ``max_size``, ``hits``, and ``misses``.
        """
        return {
            "size": self.size,
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
        }
