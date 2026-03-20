"""Startup validation for secrets and environment configuration."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.config import Settings

logger = logging.getLogger(__name__)


def validate_settings(settings: "Settings") -> list[str]:
    """Validate configuration and return a list of warning/error messages.

    Checks that required API keys are present for the configured providers.
    Logs warnings and errors but never raises — the health endpoint will
    report degraded status instead.
    """
    messages: list[str] = []

    # ── LLM provider checks ─────────────────────────────────────────
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY is None:
        msg = "LLM_PROVIDER is 'openai' but OPENAI_API_KEY is not set. LLM calls will fail until the key is configured."
        logger.warning(msg)
        messages.append(msg)

    if (
        settings.LLM_PROVIDER == "anthropic"
        and settings.ANTHROPIC_API_KEY is None
        and settings.ANTHROPIC_AUTH_TOKEN is None
    ):
        msg = (
            "LLM_PROVIDER is 'anthropic' but neither ANTHROPIC_API_KEY nor "
            "ANTHROPIC_AUTH_TOKEN is set. LLM calls will fail until credentials are configured."
        )
        logger.warning(msg)
        messages.append(msg)

    if settings.LLM_PROVIDER == "cloudflare" and (
        not settings.CLOUDFLARE_ACCOUNT_ID or not settings.CLOUDFLARE_API_TOKEN
    ):
        msg = (
            "LLM_PROVIDER is 'cloudflare' but CLOUDFLARE_ACCOUNT_ID and/or "
            "CLOUDFLARE_API_TOKEN are not set. "
            "LLM calls will fail until both are configured."
        )
        logger.warning(msg)
        messages.append(msg)

    # ── Embedding provider checks ────────────────────────────────────
    if settings.EMBEDDING_PROVIDER == "cloudflare" and (
        not settings.CLOUDFLARE_ACCOUNT_ID or not settings.CLOUDFLARE_API_TOKEN
    ):
        msg = (
            "EMBEDDING_PROVIDER is 'cloudflare' but CLOUDFLARE_ACCOUNT_ID and/or "
            "CLOUDFLARE_API_TOKEN are not set. "
            "Embeddings will not work — document ingestion and search are unavailable."
        )
        logger.error(msg)
        messages.append(msg)

    if settings.EMBEDDING_PROVIDER == "openai" and settings.OPENAI_API_KEY is None:
        msg = (
            "EMBEDDING_PROVIDER is 'openai' but OPENAI_API_KEY is not set. "
            "Embeddings will not work — document ingestion and search are unavailable."
        )
        logger.error(msg)
        messages.append(msg)

    if settings.EMBEDDING_PROVIDER == "ollama":
        msg = (
            f"EMBEDDING_PROVIDER is 'ollama', using OLLAMA_BASE_URL={settings.OLLAMA_BASE_URL} "
            f"with model={settings.OLLAMA_EMBEDDING_MODEL}."
        )
        logger.info(msg)
        # Info-level messages are not appended to the warnings/errors list.

    return messages
