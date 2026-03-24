"""Generation service — orchestrates the full RAG pipeline.

Retrieves relevant chunks, checks confidence, and generates a streaming
answer with citations using the configured LLM provider. Pure Python — no
FastAPI imports.
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any

from app.core.constants import MAX_HISTORY_MESSAGES
from app.core.exceptions import ProviderError
from app.services.confidence import calculate_confidence, should_abstain
from app.services.retrieval import retrieve_relevant_chunks
from app.services.summarization import summarize_history

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from chromadb.api.models.Collection import Collection

    from app.config import Settings
    from app.core.models import Citation
    from app.plugins.pipeline import PluginPipeline
    from app.providers.base import EmbeddingProvider, LLMProvider
    from app.services.cache import EmbeddingCache

logger = logging.getLogger(__name__)

ABSTAIN_MESSAGE = "I don't have enough information in the uploaded documents to answer this question."


def get_llm_provider(settings: Settings) -> LLMProvider:
    """Return an LLM provider instance based on the configured provider name.

    Args:
        settings: Application settings containing provider config and API keys.

    Returns:
        An LLM provider satisfying the ``LLMProvider`` protocol.

    Raises:
        ProviderError: If the configured provider is unknown or missing
            required credentials.
    """
    provider = settings.LLM_PROVIDER

    if provider == "ollama":
        from app.providers.ollama import OllamaProvider

        return OllamaProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )

    if provider == "anthropic":
        from app.providers.anthropic_provider import AnthropicProvider

        auth_token = settings.ANTHROPIC_AUTH_TOKEN
        if not settings.ANTHROPIC_API_KEY and not auth_token:
            raise ProviderError(
                provider="anthropic",
                reason="ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN is not set",
            )
        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            auth_token=auth_token,
        )

    if provider == "openai":
        from app.providers.openai_provider import OpenAIProvider

        if not settings.OPENAI_API_KEY:
            raise ProviderError(
                provider="openai",
                reason="OPENAI_API_KEY is not set",
            )
        return OpenAIProvider(api_key=settings.OPENAI_API_KEY)

    if provider == "cloudflare":
        from app.providers.openai_provider import OpenAIProvider

        if not settings.CLOUDFLARE_API_TOKEN or not settings.CLOUDFLARE_ACCOUNT_ID:
            raise ProviderError(
                provider="cloudflare",
                reason="CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN are required when LLM_PROVIDER=cloudflare",
            )
        base_url = f"https://api.cloudflare.com/client/v4/accounts/{settings.CLOUDFLARE_ACCOUNT_ID}/ai/v1"
        return OpenAIProvider(
            api_key=settings.CLOUDFLARE_API_TOKEN,
            model=settings.CLOUDFLARE_LLM_MODEL,
            base_url=base_url,
        )

    raise ProviderError(
        provider=provider,
        reason=f"Unknown LLM provider: {provider}",
    )


def build_context(citations: list[Citation]) -> str:
    """Build a context string from retrieved citations for the LLM prompt.

    Each citation is formatted as a numbered source block containing
    the document name, chunk index, and the chunk content.

    Args:
        citations: The list of retrieved citations ordered by relevance.

    Returns:
        A formatted context string ready for LLM consumption.
    """
    if not citations:
        return ""

    parts: list[str] = []
    for i, citation in enumerate(citations, start=1):
        location = f"page {citation.page_number}, " if citation.page_number else ""
        parts.append(
            f"[Source {i}] {citation.document_name} ({location}chunk {citation.chunk_index}):\n{citation.chunk_content}"
        )

    return "\n\n".join(parts)


def _serialize_citations(citations: list[Citation]) -> str:
    """Serialize a list of citations to a JSON string.

    Args:
        citations: Citations to serialize.

    Returns:
        A JSON string representation of the citations list.
    """
    return json.dumps(
        [
            {
                "documentId": str(c.document_id),
                "documentName": c.document_name,
                "chunkContent": c.chunk_content,
                "chunkIndex": c.chunk_index,
                "relevanceScore": c.relevance_score,
                "pageNumber": c.page_number,
            }
            for c in citations
        ]
    )


def build_generation_kwargs(settings: Settings) -> dict[str, Any]:
    """Build keyword arguments for the LLM provider from application settings.

    Reads ``SYSTEM_PROMPT``, ``LLM_TEMPERATURE``, ``LLM_TOP_P``, and
    ``LLM_MAX_TOKENS`` from the in-memory Settings singleton (synced by the
    settings router on every PUT) to avoid redundant disk I/O per request.

    Args:
        settings: Application settings containing LLM generation parameters.

    Returns:
        A dict with keys ``temperature``, ``top_p``, ``max_tokens``, and
        optionally ``system_prompt`` (included only when non-empty).
    """
    kwargs: dict[str, Any] = {}

    system_prompt = settings.SYSTEM_PROMPT
    if system_prompt:
        kwargs["system_prompt"] = system_prompt

    kwargs["temperature"] = settings.LLM_TEMPERATURE
    kwargs["top_p"] = settings.LLM_TOP_P
    kwargs["max_tokens"] = settings.LLM_MAX_TOKENS

    return kwargs


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
    plugin_pipeline: PluginPipeline | None = None,
) -> AsyncIterator[str]:
    """Run the RAG pipeline and stream the answer as SSE-formatted events.

    Yields Server-Sent Events in this order:
      1. ``token`` events — individual text chunks as they are generated
      2. A single ``citations`` event — JSON-encoded citation list
      3. A single ``done`` event — signals end of stream

    If confidence is too low, yields the guardrail message as a single
    token event followed by citations (empty) and done.

    If an error occurs during generation, yields an ``error`` event.

    Args:
        query: The user's natural-language question.
        settings: Application settings (provider config, API keys, etc.).
        collection: Optional ChromaDB collection for retrieval.
        history: Optional conversation history (last N messages) for
            multi-turn context. Truncated to ``MAX_HISTORY_MESSAGES``.
        document_ids: Optional list of document IDs to scope the search.
        embedder: Optional singleton embedding provider (from app.state).
        embedding_cache: Optional embedding cache for query embeddings.
        user_id: Optional user namespace for multi-user document isolation.

    Yields:
        SSE-formatted strings (``event: <type>\\ndata: <payload>\\n\\n``).
    """
    # 0. Create a request-scoped copy of the pipeline to avoid trace conflicts
    #    between concurrent requests sharing the same singleton pipeline.
    if plugin_pipeline is not None:
        from app.plugins.pipeline import PluginPipeline as _PluginPipeline

        plugin_pipeline = _PluginPipeline(plugin_pipeline.plugins)
        plugin_pipeline.clear_trace()

    # 0a. Run on_retrieve plugin hook (e.g. query rewriting)
    retrieval_query = query
    if plugin_pipeline is not None:
        retrieval_query = plugin_pipeline.run_on_retrieve(query)

    # 1. Retrieve relevant chunks
    citations = await retrieve_relevant_chunks(
        retrieval_query,
        settings,
        collection=collection,
        document_ids=document_ids,
        embedder=embedder,
        embedding_cache=embedding_cache,
        user_id=user_id,
    )

    # 2. Calculate confidence
    confidence = calculate_confidence(citations)

    # 3. Guardrail: abstain if confidence is too low
    if should_abstain(confidence):
        yield _format_sse("token", ABSTAIN_MESSAGE)
        yield _format_sse("citations", "[]")
        yield _format_sse(
            "done",
            json.dumps({"confidence": confidence}),
        )
        return

    # 4. Build context and stream LLM response
    context = build_context(citations)

    # 4a. Run on_generate plugin hook (e.g. prompt/context transformation)
    if plugin_pipeline is not None:
        result = plugin_pipeline.run_on_generate(query, context)
        if isinstance(result, tuple) and len(result) == 2:
            query, context = result

    provider = llm_provider or get_llm_provider(settings)

    # Summarize older history or fall back to truncation
    raw_history = history or []
    summary: str | None = None
    if raw_history:
        try:
            summary, recent_history = await summarize_history(raw_history, provider)
        except Exception:
            logger.warning("summarize_history raised, falling back to truncation", exc_info=True)
            summary = None
            recent_history = raw_history[-MAX_HISTORY_MESSAGES:]
    else:
        recent_history = []

    # If summarization produced a summary, prepend it as a system message
    effective_history: list[dict] = []
    if summary:
        effective_history.append({"role": "system", "content": f"Previous conversation summary: {summary}"})
    effective_history.extend(recent_history)

    # Build generation kwargs from settings overlay
    gen_kwargs = build_generation_kwargs(settings)

    answer_tokens: list[str] = []
    try:
        async for token in provider.generate_stream(query, context, history=effective_history or None, **gen_kwargs):
            if plugin_pipeline is not None:
                answer_tokens.append(token)
            yield _format_sse("token", token)
    except ProviderError as exc:
        yield _format_sse("error", str(exc))
        return

    # 5. Run post-generation plugin hooks (if pipeline provided)
    if plugin_pipeline is not None:
        plugin_pipeline.run_on_post_generate("".join(answer_tokens))

    # 6. Send citations and done events
    yield _format_sse("citations", _serialize_citations(citations))

    # 7. Emit plugin trace if pipeline was provided
    if plugin_pipeline is not None:
        trace = plugin_pipeline.get_trace()
        trace_payload = json.dumps(
            [
                {
                    "pluginName": entry["plugin"],
                    "hookName": entry["hook"],
                    "durationMs": entry["duration_ms"],
                    "error": bool(entry.get("error")),
                }
                for entry in trace
            ]
        )
        yield _format_sse("plugin_trace", trace_payload)

    # 8. Emit summary event if summarization occurred
    if summary:
        yield _format_sse("summary", json.dumps({"summary": summary}))

    yield _format_sse(
        "done",
        json.dumps({"confidence": confidence}),
    )


def _format_sse(event: str, data: str) -> str:
    """Format a payload as a Server-Sent Event string.

    Handles multi-line data by prefixing each line with ``data: ``
    per the SSE specification.

    Args:
        event: The event type (e.g., "token", "citations", "done", "error").
        data: The event payload string.

    Returns:
        An SSE-formatted string.
    """
    lines = "\n".join(f"data: {line}" for line in data.split("\n"))
    return f"event: {event}\n{lines}\n\n"
