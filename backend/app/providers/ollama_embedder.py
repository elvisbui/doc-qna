"""Ollama embedding provider implementation.

Uses Ollama's /api/embed endpoint to generate text embeddings locally.
Satisfies the EmbeddingProvider protocol defined in providers/base.py.
"""

import asyncio

import httpx

from app.config import get_settings
from app.core.exceptions import ProviderError
from app.providers.ollama_utils import ensure_model_available

_PROVIDER_NAME = "ollama-embedder"


class OllamaEmbedder:
    """Generate text embeddings using a local Ollama instance.

    Args:
        base_url: The Ollama server base URL (e.g. ``http://localhost:11434``).
        model: The embedding model name. Defaults to ``"nomic-embed-text"``.
    """

    def __init__(self, base_url: str, model: str = "nomic-embed-text") -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=120.0)
        self._auto_pull = get_settings().OLLAMA_AUTO_PULL
        self._model_checked = False

    async def _ensure_model(self) -> None:
        """Check model availability once, on first use (non-blocking)."""
        if self._model_checked or not self._auto_pull:
            return
        self._model_checked = True
        await asyncio.to_thread(ensure_model_available, self._base_url, self._model)

    async def embed(self, text: str) -> list[float]:
        """Embed a single text into a vector.

        Args:
            text: The text to embed.

        Returns:
            A list of floats representing the embedding vector.
            Returns an empty list if the input text is empty.
        """
        if not text:
            return []

        await self._ensure_model()
        try:
            response = await self._client.post(
                "/api/embed",
                json={"model": self._model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"][0]
        except httpx.HTTPError as exc:
            raise ProviderError(provider=_PROVIDER_NAME, reason=str(exc)) from exc
        except (KeyError, IndexError) as exc:
            raise ProviderError(provider=_PROVIDER_NAME, reason=f"Unexpected response format: {exc}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts into vectors.

        Ollama's /api/embed endpoint accepts a list of inputs natively.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
            Returns an empty list if the input list is empty.
        """
        if not texts:
            return []

        await self._ensure_model()
        try:
            response = await self._client.post(
                "/api/embed",
                json={"model": self._model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()
            return data["embeddings"]
        except httpx.HTTPError as exc:
            raise ProviderError(provider=_PROVIDER_NAME, reason=str(exc)) from exc
        except (KeyError, IndexError) as exc:
            raise ProviderError(provider=_PROVIDER_NAME, reason=f"Unexpected response format: {exc}") from exc
