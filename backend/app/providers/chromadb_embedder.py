"""ChromaDB default embedding provider — uses the built-in all-MiniLM-L6-v2 model.

Runs locally with no API key required. Useful for development and testing.
"""

import asyncio

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction


class ChromaDBEmbedder:
    """Generate embeddings using ChromaDB's built-in sentence-transformer model.

    Satisfies the ``EmbeddingProvider`` protocol through structural subtyping.
    """

    def __init__(self) -> None:
        self._ef = DefaultEmbeddingFunction()

    async def embed(self, text: str) -> list[float]:
        """Embed a single text into a vector."""
        if not text:
            return []
        result = await asyncio.to_thread(self._ef, [text])
        return [float(x) for x in result[0]]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts into vectors."""
        if not texts:
            return []
        result = await asyncio.to_thread(self._ef, texts)
        return [[float(x) for x in v] for v in result]
