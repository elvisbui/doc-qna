"""Embedding provider implementations and factory.

Contains the OpenAI embedder and a factory function that returns the
correct embedder based on the configured EMBEDDING_PROVIDER setting.
"""

from openai import APIError, AsyncOpenAI

from app.config import Settings
from app.core.exceptions import ProviderError
from app.providers.base import EmbeddingProvider

_PROVIDER_NAME = "openai-embedder"


class OpenAIEmbedder:
    """Generate text embeddings using OpenAI's embedding models.

    This class satisfies the ``EmbeddingProvider`` protocol through
    structural subtyping — it implements matching ``embed`` and
    ``embed_batch`` async methods without inheriting from the protocol.

    Args:
        api_key: OpenAI API key for authentication.
        model: The embedding model identifier. Defaults to
            ``"text-embedding-3-small"``.
    """

    def __init__(self, api_key: str, model: str = "text-embedding-3-small", base_url: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

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

        try:
            response = await self._client.embeddings.create(
                input=text,
                model=self._model,
            )
            return response.data[0].embedding
        except APIError as exc:
            raise ProviderError(provider=_PROVIDER_NAME, reason=str(exc)) from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple texts into vectors in a single API call.

        Args:
            texts: A list of texts to embed.

        Returns:
            A list of embedding vectors, one per input text.
            Returns an empty list if the input list is empty.
        """
        if not texts:
            return []

        try:
            response = await self._client.embeddings.create(
                input=texts,
                model=self._model,
            )
            sorted_data = sorted(response.data, key=lambda item: item.index)
            return [item.embedding for item in sorted_data]
        except APIError as exc:
            raise ProviderError(provider=_PROVIDER_NAME, reason=str(exc)) from exc


def get_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Return an embedding provider instance based on the configured setting.

    Args:
        settings: Application settings containing provider config and API keys.

    Returns:
        An embedding provider satisfying the ``EmbeddingProvider`` protocol.

    Raises:
        ProviderError: If the configured provider is unknown or missing
            required credentials.
    """
    provider = settings.EMBEDDING_PROVIDER

    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise ProviderError(
                provider="openai-embedder",
                reason="OPENAI_API_KEY is required when EMBEDDING_PROVIDER=openai",
            )
        return OpenAIEmbedder(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
        )

    if provider == "ollama":
        from app.providers.ollama_embedder import OllamaEmbedder

        return OllamaEmbedder(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_EMBEDDING_MODEL,
        )

    if provider == "chromadb":
        from app.providers.chromadb_embedder import ChromaDBEmbedder

        return ChromaDBEmbedder()

    if provider == "cloudflare":
        if not settings.CLOUDFLARE_API_TOKEN or not settings.CLOUDFLARE_ACCOUNT_ID:
            raise ProviderError(
                provider="cloudflare-embedder",
                reason="CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required when EMBEDDING_PROVIDER=cloudflare",
            )
        base_url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/ai/v1"
        return OpenAIEmbedder(
            api_key=settings.CLOUDFLARE_API_TOKEN,
            model=settings.CLOUDFLARE_EMBEDDING_MODEL,
            base_url=base_url,
        )

    raise ProviderError(
        provider=str(provider),
        reason=f"Unknown embedding provider: {provider}",
    )
