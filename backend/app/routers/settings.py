"""Settings router — GET/PUT /api/settings.

Provides runtime configuration management with a JSON file overlay.
Environment variables provide defaults; the overlay file stores user overrides.
"""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.core.constants import CHUNK_OVERLAP, CHUNK_SIZE
from app.core.overlay import load_overlay, save_overlay
from app.schemas.settings import (
    ApiKeyUpdateRequest,
    ConnectionTestRequest,
    ConnectionTestResponse,
    PromptPreset,
    SettingsResponse,
    SettingsUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _close_old_provider_client(app_state: object, attr: str) -> None:
    """Close the httpx client on an existing provider before replacing it.

    Args:
        app_state: The FastAPI application state object holding provider
            singletons.
        attr: The attribute name on ``app_state`` whose provider client
            should be closed (e.g. ``"llm_provider"``).
    """
    old_provider = getattr(app_state, attr, None)
    old_client = getattr(old_provider, "_client", None)
    if old_client is not None:
        if hasattr(old_client, "aclose"):
            await old_client.aclose()
        elif hasattr(old_client, "close"):
            close_result = old_client.close()
            if close_result is not None:
                await close_result


def _mask_key(key: str | None) -> str:
    """Return a masked version of an API key showing only the last 4 chars."""
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]


def _build_response() -> SettingsResponse:
    """Merge env defaults with the user overlay and return a SettingsResponse.

    Returns:
        A ``SettingsResponse`` containing the effective runtime settings
        with API keys masked.
    """
    settings = get_settings()
    overlay = load_overlay()

    openai_key = overlay.get("openai_api_key") or settings.OPENAI_API_KEY or ""
    anthropic_key = overlay.get("anthropic_api_key") or settings.ANTHROPIC_API_KEY or ""
    cloudflare_token = overlay.get("cloudflare_api_token") or settings.CLOUDFLARE_API_TOKEN or ""

    return SettingsResponse(
        llm_provider=overlay.get("llm_provider", settings.LLM_PROVIDER),
        ollama_base_url=settings.OLLAMA_BASE_URL,
        ollama_model=overlay.get("ollama_model", settings.OLLAMA_MODEL),
        embedding_provider=overlay.get("embedding_provider", settings.EMBEDDING_PROVIDER),
        embedding_model=overlay.get("embedding_model", settings.EMBEDDING_MODEL),
        chunking_strategy=overlay.get("chunking_strategy", settings.CHUNKING_STRATEGY),
        retrieval_strategy=overlay.get("retrieval_strategy", settings.RETRIEVAL_STRATEGY),
        chunk_size=overlay.get("chunk_size", CHUNK_SIZE),
        chunk_overlap=overlay.get("chunk_overlap", CHUNK_OVERLAP),
        log_level=overlay.get("log_level", settings.LOG_LEVEL),
        has_openai_key=bool(openai_key),
        has_anthropic_key=bool(anthropic_key),
        has_cloudflare_token=bool(cloudflare_token),
        openai_key_hint=_mask_key(openai_key),
        anthropic_key_hint=_mask_key(anthropic_key),
        cloudflare_key_hint=_mask_key(cloudflare_token),
        system_prompt=overlay.get("system_prompt", settings.SYSTEM_PROMPT),
        llm_temperature=overlay.get("llm_temperature", settings.LLM_TEMPERATURE),
        llm_top_p=overlay.get("llm_top_p", settings.LLM_TOP_P),
        llm_max_tokens=overlay.get("llm_max_tokens", settings.LLM_MAX_TOKENS),
    )


@router.get(
    "",
    response_model=SettingsResponse,
    summary="Get current settings",
    description="Return the current runtime settings, merging environment defaults with any user overrides.",
)
async def get_current_settings() -> SettingsResponse:
    """Return current runtime settings."""
    return _build_response()


@router.get(
    "/presets",
    summary="List system prompt presets",
    description="Return the list of built-in system prompt presets.",
)
async def get_presets() -> list[PromptPreset]:
    """Return built-in system prompt presets from the JSON data file."""
    try:
        return _load_presets()
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load presets: {exc}",
        ) from exc


@functools.lru_cache(maxsize=1)
def _load_presets() -> list[PromptPreset]:
    """Load and cache presets from disk (called once, cached forever).

    Returns:
        A list of ``PromptPreset`` objects parsed from
        ``data/prompt_presets.json``.

    Raises:
        FileNotFoundError: If the presets JSON file does not exist.
        ValueError: If the JSON content cannot be parsed or validated.
    """
    presets_path = Path(__file__).resolve().parent.parent / "data" / "prompt_presets.json"
    if not presets_path.exists():
        raise FileNotFoundError("Presets data file not found.")
    with open(presets_path, encoding="utf-8") as f:
        raw = json.load(f)
    return [PromptPreset.model_validate(item) for item in raw]


@router.put(
    "",
    response_model=SettingsResponse,
    summary="Update settings",
    description=(
        "Update runtime settings. Only the provided fields are changed. API keys cannot be updated via this endpoint."
    ),
)
async def update_settings(body: SettingsUpdateRequest, request: Request) -> SettingsResponse:
    """Accept a partial update and persist to the overlay file."""
    updates = body.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    # Validate chunk_overlap < chunk_size when both or either are provided.
    overlay = load_overlay()
    merged = {**overlay, **updates}
    effective_chunk_size = merged.get("chunk_size", CHUNK_SIZE)
    effective_chunk_overlap = merged.get("chunk_overlap", CHUNK_OVERLAP)
    if effective_chunk_overlap >= effective_chunk_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"chunk_overlap ({effective_chunk_overlap}) must be less than chunk_size ({effective_chunk_size}).",
        )

    # Merge into existing overlay and save.
    overlay.update(updates)
    save_overlay(overlay)

    # Re-instantiate providers if provider or model settings changed.
    _LLM_FIELDS = {"llm_provider", "ollama_model", "ollama_base_url"}
    _EMBED_FIELDS = {"embedding_provider", "embedding_model"}

    settings = get_settings()

    # Sync updated overlay values to the in-memory Settings singleton so that
    # provider factory functions read the correct values.
    _OVERLAY_TO_SETTINGS = {
        "llm_provider": "LLM_PROVIDER",
        "ollama_model": "OLLAMA_MODEL",
        "ollama_base_url": "OLLAMA_BASE_URL",
        "embedding_provider": "EMBEDDING_PROVIDER",
        "embedding_model": "EMBEDDING_MODEL",
        "chunking_strategy": "CHUNKING_STRATEGY",
        "retrieval_strategy": "RETRIEVAL_STRATEGY",
        "system_prompt": "SYSTEM_PROMPT",
        "llm_temperature": "LLM_TEMPERATURE",
        "llm_top_p": "LLM_TOP_P",
        "llm_max_tokens": "LLM_MAX_TOKENS",
    }
    for overlay_key, settings_attr in _OVERLAY_TO_SETTINGS.items():
        if overlay_key in updates:
            object.__setattr__(settings, settings_attr, updates[overlay_key])

    # Warn once at config-change time if system prompt drops RAG context.
    if "system_prompt" in updates:
        prompt = updates["system_prompt"]
        if prompt and "{context}" not in prompt:
            logger.warning(
                "Custom system prompt does not contain '{context}' placeholder — "
                "retrieved document context will not be included in LLM calls"
            )

    if _LLM_FIELDS & updates.keys():
        try:
            from app.services.generation import get_llm_provider

            await _close_old_provider_client(request.app.state, "llm_provider")
            request.app.state.llm_provider = get_llm_provider(settings)
            logger.info("LLM provider re-initialized after settings change")
        except Exception as exc:
            logger.warning("Failed to re-initialize LLM provider: %s", exc)

    if _EMBED_FIELDS & updates.keys():
        try:
            from app.providers.embedder import get_embedding_provider

            await _close_old_provider_client(request.app.state, "embedder")
            request.app.state.embedder = get_embedding_provider(settings)
            logger.info("Embedding provider re-initialized after settings change")
        except Exception as exc:
            logger.warning("Failed to re-initialize embedding provider: %s", exc)

    logger.info("Settings updated: %s", list(updates.keys()))
    return _build_response()


def _format_size(size_bytes: int) -> str:
    """Convert bytes to a human-readable size string.

    Args:
        size_bytes: The size in bytes to format.

    Returns:
        A string like ``"1.5 GB"``, ``"256.0 MB"``, or ``"12.3 KB"``.
    """
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    if size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    return f"{size_bytes / 1_000:.1f} KB"


@router.get(
    "/ollama-models",
    summary="List available Ollama models",
    description="Fetches the list of locally available models from the configured Ollama instance.",
)
async def get_ollama_models() -> dict:
    """Query Ollama's /api/tags endpoint and return available models.

    Returns:
        A dict with a ``"models"`` list (each entry has ``name``, ``size``,
        ``modified``) and an optional ``"error"`` string on failure.
    """
    settings = get_settings()
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()

        data = resp.json()
        models = [
            {
                "name": m.get("name", ""),
                "size": _format_size(m.get("size", 0)),
                "modified": m.get("modified_at", ""),
            }
            for m in data.get("models", [])
        ]
        return {"models": models}

    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        logger.warning("Could not reach Ollama at %s: %s", base_url, exc)
        return {"models": [], "error": f"Could not connect to Ollama at {base_url}"}
    except httpx.HTTPStatusError as exc:
        logger.warning("Ollama returned error: %s", exc)
        return {"models": [], "error": f"Ollama returned status {exc.response.status_code}"}
    except Exception as exc:
        logger.warning("Unexpected error fetching Ollama models: %s", exc)
        return {"models": [], "error": str(exc)}


@router.post(
    "/test-connection",
    response_model=ConnectionTestResponse,
    summary="Test provider connection",
    description="Test connectivity to the specified LLM provider using the given configuration.",
)
async def test_connection(body: ConnectionTestRequest) -> ConnectionTestResponse:
    """Test connectivity to an LLM provider.

    Args:
        body: Request containing the provider name and optional config
            such as API keys or base URLs to test.

    Returns:
        A ``ConnectionTestResponse`` with ``status`` (``"ok"`` or ``"error"``)
        and a human-readable ``message``.
    """
    provider = body.provider
    config = body.config

    try:
        if provider == "ollama":
            base_url = config.get("base_url", "").rstrip("/") or get_settings().OLLAMA_BASE_URL.rstrip("/")
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/api/tags")
                resp.raise_for_status()
            model_count = len(resp.json().get("models", []))
            return ConnectionTestResponse(
                status="ok",
                message=f"Ollama is reachable at {base_url} ({model_count} model(s) available).",
            )

        elif provider == "openai":
            api_key = config.get("api_key") or (get_settings().OPENAI_API_KEY or "")
            if not api_key:
                return ConnectionTestResponse(
                    status="error",
                    message="No OpenAI API key configured.",
                )
            if not api_key.startswith("sk-"):
                return ConnectionTestResponse(
                    status="error",
                    message="Invalid OpenAI API key format (expected prefix 'sk-').",
                )
            # Try listing models to verify the key works.
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                resp.raise_for_status()
            return ConnectionTestResponse(
                status="ok",
                message="OpenAI API key is valid.",
            )

        elif provider == "anthropic":
            api_key = config.get("api_key") or (get_settings().ANTHROPIC_API_KEY or "")
            if not api_key:
                return ConnectionTestResponse(
                    status="error",
                    message="No Anthropic API key configured.",
                )
            if not api_key.startswith("sk-ant-"):
                return ConnectionTestResponse(
                    status="error",
                    message="Invalid Anthropic API key format (expected prefix 'sk-ant-').",
                )
            return ConnectionTestResponse(
                status="ok",
                message="Anthropic API key format is valid.",
            )

        elif provider == "cloudflare":
            api_token = config.get("api_token") or (get_settings().CLOUDFLARE_API_TOKEN or "")
            account_id = config.get("account_id") or (get_settings().CLOUDFLARE_ACCOUNT_ID or "")
            if not api_token or not account_id:
                return ConnectionTestResponse(
                    status="error",
                    message="Cloudflare Account ID and API Token are required.",
                )
            base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/v1"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    f"{base_url}/models",
                    headers={"Authorization": f"Bearer {api_token}"},
                )
                resp.raise_for_status()
            return ConnectionTestResponse(
                status="ok",
                message="Cloudflare Workers AI is reachable.",
            )

        else:
            return ConnectionTestResponse(
                status="error",
                message=f"Unknown provider: {provider}",
            )

    except httpx.TimeoutException:
        return ConnectionTestResponse(
            status="error",
            message=f"Connection to {provider} timed out after 5 seconds.",
        )
    except httpx.ConnectError as exc:
        return ConnectionTestResponse(
            status="error",
            message=f"Could not connect to {provider}: {exc}",
        )
    except httpx.HTTPStatusError as exc:
        return ConnectionTestResponse(
            status="error",
            message=f"{provider} returned HTTP {exc.response.status_code}.",
        )
    except Exception as exc:
        logger.warning("Unexpected error testing %s connection: %s", provider, exc)
        return ConnectionTestResponse(
            status="error",
            message=f"Unexpected error: {exc}",
        )


async def _reinit_providers_for_keys(updates: dict[str, str], settings: object, request: Request) -> None:
    """Re-instantiate LLM/embedding providers when their API keys change.

    Checks which keys were updated and, if the active provider uses that key,
    closes the old provider client and creates a new one on ``app.state``.

    Args:
        updates: Mapping of overlay key names to their new values
            (e.g. ``{"openai_api_key": "sk-..."}``).
        settings: The in-memory ``Settings`` singleton with updated key values.
        request: The current FastAPI request, used to access ``app.state``.
    """
    if "openai_api_key" in updates:
        # OpenAI key affects both embedder (if openai) and LLM (if openai)
        if getattr(settings, "EMBEDDING_PROVIDER", "") == "openai":
            try:
                from app.providers.embedder import get_embedding_provider

                await _close_old_provider_client(request.app.state, "embedder")
                request.app.state.embedder = get_embedding_provider(settings)
                logger.info("Embedding provider re-initialized after API key change")
            except Exception as exc:
                logger.warning("Failed to re-initialize embedding provider: %s", exc)
        if getattr(settings, "LLM_PROVIDER", "") == "openai":
            try:
                from app.services.generation import get_llm_provider

                await _close_old_provider_client(request.app.state, "llm_provider")
                request.app.state.llm_provider = get_llm_provider(settings)
                logger.info("LLM provider re-initialized after API key change")
            except Exception as exc:
                logger.warning("Failed to re-initialize LLM provider: %s", exc)

    if "anthropic_api_key" in updates and getattr(settings, "LLM_PROVIDER", "") == "anthropic":
        try:
            from app.services.generation import get_llm_provider

            await _close_old_provider_client(request.app.state, "llm_provider")
            request.app.state.llm_provider = get_llm_provider(settings)
            logger.info("LLM provider re-initialized after API key change")
        except Exception as exc:
            logger.warning("Failed to re-initialize LLM provider: %s", exc)

    if "cloudflare_api_token" in updates:
        if getattr(settings, "EMBEDDING_PROVIDER", "") == "cloudflare":
            try:
                from app.providers.embedder import get_embedding_provider

                await _close_old_provider_client(request.app.state, "embedder")
                request.app.state.embedder = get_embedding_provider(settings)
                logger.info("Embedding provider re-initialized after API key change")
            except Exception as exc:
                logger.warning("Failed to re-initialize embedding provider: %s", exc)
        if getattr(settings, "LLM_PROVIDER", "") == "cloudflare":
            try:
                from app.services.generation import get_llm_provider

                await _close_old_provider_client(request.app.state, "llm_provider")
                request.app.state.llm_provider = get_llm_provider(settings)
                logger.info("LLM provider re-initialized after API key change")
            except Exception as exc:
                logger.warning("Failed to re-initialize LLM provider: %s", exc)


@router.post(
    "/api-keys",
    response_model=SettingsResponse,
    summary="Update API keys",
    description=(
        "Store OpenAI and/or Anthropic API keys in the settings overlay file. "
        "Keys are never returned via GET — only boolean status is exposed."
    ),
)
async def update_api_keys(body: ApiKeyUpdateRequest, request: Request) -> SettingsResponse:
    """Accept API key updates and persist to the overlay file.

    Stores the provided keys in the overlay, updates the in-memory settings,
    and re-initializes any affected provider singletons.

    Args:
        body: Request containing one or more API keys to update.
        request: The current FastAPI request, used to access ``app.state``.

    Returns:
        The updated ``SettingsResponse`` reflecting the new key status.

    Raises:
        HTTPException: If no API keys are provided in the request body
            (400 Bad Request).
    """
    updates: dict[str, str] = {}

    if body.openai_api_key is not None:
        updates["openai_api_key"] = body.openai_api_key
    if body.anthropic_api_key is not None:
        updates["anthropic_api_key"] = body.anthropic_api_key
    if body.cloudflare_api_token is not None:
        updates["cloudflare_api_token"] = body.cloudflare_api_token
    if body.cloudflare_account_id is not None:
        updates["cloudflare_account_id"] = body.cloudflare_account_id

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one API key must be provided.",
        )

    overlay = load_overlay()
    overlay.update(updates)
    save_overlay(overlay)

    # Also update in-memory settings so the keys take effect immediately.
    settings = get_settings()
    if "openai_api_key" in updates:
        object.__setattr__(settings, "OPENAI_API_KEY", updates["openai_api_key"])
    if "anthropic_api_key" in updates:
        object.__setattr__(settings, "ANTHROPIC_API_KEY", updates["anthropic_api_key"])
    if "cloudflare_api_token" in updates:
        object.__setattr__(settings, "CLOUDFLARE_API_TOKEN", updates["cloudflare_api_token"])
    if "cloudflare_account_id" in updates:
        object.__setattr__(settings, "CLOUDFLARE_ACCOUNT_ID", updates["cloudflare_account_id"])

    # Re-instantiate provider singletons so they pick up the new keys.
    await _reinit_providers_for_keys(updates, settings, request)

    logger.info("API keys updated: %s", [k.replace("_api_key", "") for k in updates])
    return _build_response()
