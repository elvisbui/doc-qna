"""Generation service — orchestrates the full RAG pipeline."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.core.constants import MAX_HISTORY_MESSAGES
from app.core.exceptions import ProviderError
from app.services.confidence import calculate_confidence, should_abstain
from app.services.retrieval import retrieve_relevant_chunks

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from chromadb.api.models.Collection import Collection

    from app.config import Settings
    from app.core.models import Citation
    from app.providers.base import EmbeddingProvider, LLMProvider
    from app.services.cache import EmbeddingCache

logger = logging.getLogger(__name__)

ABSTAIN_MESSAGE = (
    "I don't have enough information in the uploaded documents to answer this question."
)


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Return an LLM provider instance based on the configured provider name."""
    provider = settings.LLM_PROVIDER

    if provider == "ollama":
        from app.providers.ollama import OllamaProvider
        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )

    if provider == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider
        if not settings.ANTHROPIC_API_KEY:
            raise ProviderError(provider="anthropic", reason="ANTHROPIC_API_KEY is not set")
        return AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY)

    if provider == "openai":
        from app.providers.openai_provider import OpenAIProvider
        if not settings.OPENAI_API_KEY:
            raise ProviderError(provider="openai", reason="OPENAI_API_KEY is not set")
        return OpenAIProvider(api_key=settings.OPENAI_API_KEY)

    raise ProviderError(provider=provider, reason=f"Unknown LLM provider: {provider}")


def build_context(citations: list[Citation]) -> str:
    """Build a context string from retrieved citations for the LLM prompt."""
    if not citations:
        return ""
    parts: list[str] = []
    for i, citation in enumerate(citations, start=1):
        parts.append(
            f"[Source {i}] {citation.document_name} "
            f"(chunk {citation.chunk_index}):\n"
            f"{citation.chunk_content}"
        )
    return "\n\n".join(parts)


def _serialize_citations(citations: list[Citation]) -> str:
    return json.dumps([
        {
            "documentId": str(c.document_id),
            "documentName": c.document_name,
            "chunkContent": c.chunk_content,
            "chunkIndex": c.chunk_index,
            "relevanceScore": c.relevance_score,
        }
        for c in citations
    ])


async def generate_answer_stream(
    query: str,
    settings: Settings,
    collection: Collection | None = None,
    history: list[dict] | None = None,
    document_ids: list[str] | None = None,
    embedder: EmbeddingProvider | None = None,
    embedding_cache: EmbeddingCache | None = None,
    user_id: str | None = None,
    llm_provider: LLMProvider | None = None,
) -> AsyncIterator[str]:
    """Run the RAG pipeline and stream the answer as SSE-formatted events."""
    # 1. Retrieve relevant chunks
    citations = await retrieve_relevant_chunks(
        query, settings, collection=collection,
        document_ids=document_ids, embedder=embedder,
        embedding_cache=embedding_cache, user_id=user_id,
    )

    # 2. Calculate confidence
    confidence = calculate_confidence(citations)

    # 3. Guardrail
    if should_abstain(confidence):
        yield _format_sse("token", ABSTAIN_MESSAGE)
        yield _format_sse("citations", "[]")
        yield _format_sse("done", json.dumps({"confidence": confidence}))
        return

    # 4. Build context and stream
    context = build_context(citations)
    provider = llm_provider or get_llm_provider(settings)

    effective_history = (history or [])[-MAX_HISTORY_MESSAGES:]

    try:
        async for token in provider.generate_stream(
            query, context, history=effective_history or None
        ):
            yield _format_sse("token", token)
    except ProviderError as exc:
        yield _format_sse("error", str(exc))
        return

    yield _format_sse("citations", _serialize_citations(citations))
    yield _format_sse("done", json.dumps({"confidence": confidence}))


def _format_sse(event: str, data: str) -> str:
    lines = "\n".join(f"data: {line}" for line in data.split("\n"))
    return f"event: {event}\n{lines}\n\n"
