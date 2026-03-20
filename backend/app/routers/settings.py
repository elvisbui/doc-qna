"""Settings router — GET/PUT /api/settings."""

from __future__ import annotations

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
    SettingsResponse,
    SettingsUpdateRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _close_old_provider_client(app_state: object, attr: str) -> None:
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
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return "*" * (len(key) - 4) + key[-4:]


def _build_response() -> SettingsResponse:
    settings = get_settings()
    overlay = load_overlay()

    openai_key = overlay.get("openai_api_key") or settings.OPENAI_API_KEY or ""
    anthropic_key = overlay.get("anthropic_api_key") or settings.ANTHROPIC_API_KEY or ""

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
        openai_key_hint=_mask_key(openai_key),
        anthropic_key_hint=_mask_key(anthropic_key),
        system_prompt=overlay.get("system_prompt", settings.SYSTEM_PROMPT),
        llm_temperature=overlay.get("llm_temperature", settings.LLM_TEMPERATURE),
        llm_top_p=overlay.get("llm_top_p", settings.LLM_TOP_P),
        llm_max_tokens=overlay.get("llm_max_tokens", settings.LLM_MAX_TOKENS),
    )


@router.get("", response_model=SettingsResponse, summary="Get current settings")
async def get_current_settings() -> SettingsResponse:
    return _build_response()


@router.put("", response_model=SettingsResponse, summary="Update settings")
async def update_settings(body: SettingsUpdateRequest, request: Request) -> SettingsResponse:
    updates = body.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    overlay = load_overlay()
    merged = {**overlay, **updates}
    effective_chunk_size = merged.get("chunk_size", CHUNK_SIZE)
    effective_chunk_overlap = merged.get("chunk_overlap", CHUNK_OVERLAP)
    if effective_chunk_overlap >= effective_chunk_size:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"chunk_overlap ({effective_chunk_overlap}) must be less than chunk_size ({effective_chunk_size}).",
        )

    overlay.update(updates)
    save_overlay(overlay)

    _LLM_FIELDS = {"llm_provider", "ollama_model", "ollama_base_url"}
    _EMBED_FIELDS = {"embedding_provider", "embedding_model"}
    settings = get_settings()

    _OVERLAY_TO_SETTINGS = {
        "llm_provider": "LLM_PROVIDER",
        "ollama_model": "OLLAMA_MODEL",
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

    if _LLM_FIELDS & updates.keys():
        try:
            from app.services.generation import get_llm_provider
            await _close_old_provider_client(request.app.state, "llm_provider")
            request.app.state.llm_provider = get_llm_provider(settings)
        except Exception as exc:
            logger.warning("Failed to re-initialize LLM provider: %s", exc)

    if _EMBED_FIELDS & updates.keys():
        try:
            from app.providers.embedder import get_embedding_provider
            await _close_old_provider_client(request.app.state, "embedder")
            request.app.state.embedder = get_embedding_provider(settings)
        except Exception as exc:
            logger.warning("Failed to re-initialize embedding provider: %s", exc)

    logger.info("Settings updated: %s", list(updates.keys()))
    return _build_response()


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1_000_000_000:
        return f"{size_bytes / 1_000_000_000:.1f} GB"
    if size_bytes >= 1_000_000:
        return f"{size_bytes / 1_000_000:.1f} MB"
    return f"{size_bytes / 1_000:.1f} KB"


@router.get("/ollama-models", summary="List available Ollama models")
async def get_ollama_models() -> dict:
    settings = get_settings()
    base_url = settings.OLLAMA_BASE_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/api/tags")
            resp.raise_for_status()
        data = resp.json()
        models = [{"name": m.get("name", ""), "size": _format_size(m.get("size", 0)), "modified": m.get("modified_at", "")} for m in data.get("models", [])]
        return {"models": models}
    except (httpx.ConnectError, httpx.TimeoutException) as exc:
        return {"models": [], "error": f"Could not connect to Ollama at {base_url}"}
    except Exception as exc:
        return {"models": [], "error": str(exc)}


@router.post("/test-connection", response_model=ConnectionTestResponse, summary="Test provider connection")
async def test_connection(body: ConnectionTestRequest) -> ConnectionTestResponse:
    provider = body.provider
    config = body.config
    try:
        if provider == "ollama":
            base_url = config.get("base_url", "").rstrip("/") or get_settings().OLLAMA_BASE_URL.rstrip("/")
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{base_url}/api/tags")
                resp.raise_for_status()
            return ConnectionTestResponse(status="ok", message=f"Ollama is reachable at {base_url}")
        elif provider == "openai":
            api_key = config.get("api_key") or (get_settings().OPENAI_API_KEY or "")
            if not api_key:
                return ConnectionTestResponse(status="error", message="No OpenAI API key configured.")
            return ConnectionTestResponse(status="ok", message="OpenAI API key format is valid.")
        elif provider == "anthropic":
            api_key = config.get("api_key") or (get_settings().ANTHROPIC_API_KEY or "")
            if not api_key:
                return ConnectionTestResponse(status="error", message="No Anthropic API key configured.")
            return ConnectionTestResponse(status="ok", message="Anthropic API key format is valid.")
        else:
            return ConnectionTestResponse(status="error", message=f"Unknown provider: {provider}")
    except Exception as exc:
        return ConnectionTestResponse(status="error", message=str(exc))


@router.post("/api-keys", response_model=SettingsResponse, summary="Update API keys")
async def update_api_keys(body: ApiKeyUpdateRequest, request: Request) -> SettingsResponse:
    updates: dict[str, str] = {}
    if body.openai_api_key is not None:
        updates["openai_api_key"] = body.openai_api_key
    if body.anthropic_api_key is not None:
        updates["anthropic_api_key"] = body.anthropic_api_key
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one API key must be provided.")

    overlay = load_overlay()
    overlay.update(updates)
    save_overlay(overlay)

    settings = get_settings()
    if "openai_api_key" in updates:
        object.__setattr__(settings, "OPENAI_API_KEY", updates["openai_api_key"])
    if "anthropic_api_key" in updates:
        object.__setattr__(settings, "ANTHROPIC_API_KEY", updates["anthropic_api_key"])

    logger.info("API keys updated: %s", [k.replace("_api_key", "") for k in updates])
    return _build_response()
