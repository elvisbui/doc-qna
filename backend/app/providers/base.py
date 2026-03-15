"""Protocol-based provider interfaces for LLM and embedding providers.

These protocols define the contracts that provider implementations must satisfy.
Uses structural subtyping (PEP 544) — implementations do not need to inherit
from these classes; they only need matching method signatures.

"""

from collections.abc import AsyncIterator
from typing import Any, Protocol


class LLMProvider(Protocol):
    """Interface for large language model providers.

    Any class with matching async `generate` and `generate_stream` methods
    satisfies this protocol — no inheritance required.
    """

    async def generate(self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any) -> str: ...

    async def generate_stream(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> AsyncIterator[str]: ...


class EmbeddingProvider(Protocol):
    """Interface for text embedding providers."""

    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
