"""Ollama utility functions.

Provides helpers for managing Ollama models, including automatic
model pulling when a configured model is not yet available locally.
"""

import logging

import httpx

from app.core.exceptions import ProviderError

logger = logging.getLogger(__name__)

_PULL_TIMEOUT = 600.0  # 10 minutes — model downloads can be large


def ensure_model_available(base_url: str, model: str) -> None:
    """Check whether *model* is present on the Ollama server and pull it if not.

    Args:
        base_url: The Ollama server base URL (e.g. ``http://localhost:11434``).
        model: The model name to check / pull (e.g. ``"llama3.2"``).

    Raises:
        ProviderError: If the server is unreachable or the pull fails.
    """
    base_url = base_url.rstrip("/")

    # 1. Check if model already exists via GET /api/tags
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
    except httpx.ConnectError as exc:
        raise ProviderError(
            provider="ollama",
            reason=f"Cannot connect to Ollama at {base_url}: {exc}",
        ) from exc
    except httpx.HTTPError as exc:
        raise ProviderError(
            provider="ollama",
            reason=f"Failed to list Ollama models: {exc}",
        ) from exc

    # The /api/tags response has {"models": [{"name": "llama3.2:latest", ...}, ...]}
    # Model names may or may not include a tag suffix (e.g. ":latest").
    existing_models: list[str] = [m.get("name", "") for m in data.get("models", [])]
    model_base = model.split(":")[0]

    for name in existing_models:
        if name == model or name.split(":")[0] == model_base:
            logger.debug("Ollama model '%s' is already available.", model)
            return

    # 2. Model is missing — pull it
    logger.info("Ollama model '%s' not found locally. Pulling (this may take a while)...", model)

    try:
        with (
            httpx.Client(timeout=_PULL_TIMEOUT) as client,
            client.stream("POST", f"{base_url}/api/pull", json={"name": model}) as resp,
        ):
            resp.raise_for_status()
            for line in resp.iter_lines():
                if line:
                    logger.debug("Ollama pull progress: %s", line)
    except httpx.HTTPStatusError as exc:
        raise ProviderError(
            provider="ollama",
            reason=f"Ollama model pull failed with HTTP {exc.response.status_code}: {exc.response.text}",
        ) from exc
    except httpx.HTTPError as exc:
        raise ProviderError(
            provider="ollama",
            reason=f"Ollama model pull failed: {exc}",
        ) from exc

    logger.info("Successfully pulled Ollama model '%s'.", model)
