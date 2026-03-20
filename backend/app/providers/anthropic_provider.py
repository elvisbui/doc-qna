"""Anthropic LLM provider implementation.

Supports two auth modes:
1. API key (x-api-key header) — standard console keys
2. OAuth Bearer token — for local dev with Claude Pro/Max subscription

Satisfies the ``LLMProvider`` protocol defined in providers/base.py.
"""

import asyncio
import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.constants import MAX_RESPONSE_TOKENS, SYSTEM_PROMPT_TEMPLATE
from app.core.exceptions import ProviderError

logger = logging.getLogger(__name__)

_PROVIDER_NAME = "anthropic"
_API_URL = "https://api.anthropic.com/v1/messages"
_MAX_RETRIES = 2
_RETRY_DELAY = 1.0
_TIMEOUT = 120.0


class AnthropicProvider:
    """LLM provider that calls the Anthropic Messages API.

    Satisfies the ``LLMProvider`` protocol without inheriting from it.
    """

    def __init__(
        self,
        api_key: str | None = None,
        auth_token: str | None = None,
        model: str = "claude-sonnet-4-6",
    ) -> None:
        if not api_key and not auth_token:
            raise ValueError("Either api_key or auth_token must be provided")
        self._model = model
        self._auth_token = auth_token
        self._api_key = api_key
        self._client = httpx.AsyncClient(timeout=_TIMEOUT)

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with the appropriate auth method."""
        headers: dict[str, str] = {
            "content-type": "application/json",
            "anthropic-version": "2023-06-01",
        }
        if self._auth_token:
            headers["authorization"] = f"Bearer {self._auth_token}"
            headers["anthropic-beta"] = "oauth-2025-04-20"
        elif self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def _build_messages(self, prompt: str, history: list[dict] | None = None) -> list[dict]:
        """Build the messages list with history and current query."""
        messages: list[dict] = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages

    def _build_payload(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> dict[str, Any]:
        """Build the Messages API request payload."""
        system_prompt = kwargs.get("system_prompt") or SYSTEM_PROMPT_TEMPLATE
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": kwargs.get("max_tokens", MAX_RESPONSE_TOKENS),
            "system": system_prompt.replace("{context}", context),
            "messages": self._build_messages(prompt, history),
        }
        # Anthropic API does not allow both temperature and top_p simultaneously.
        # When both are provided, prefer temperature (top_p=1.0 is the default no-op).
        if "temperature" in kwargs:
            payload["temperature"] = kwargs["temperature"]
        elif "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        return payload

    async def generate(self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any) -> str:
        """Generate a complete response from the Anthropic API."""
        payload = self._build_payload(prompt, context, history, **kwargs)
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await self._client.post(_API_URL, headers=self._build_headers(), json=payload)
                resp.raise_for_status()
                data = resp.json()
                if not data.get("content"):
                    return ""
                return data["content"][0]["text"]
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code >= 500 and attempt < _MAX_RETRIES:
                    logger.warning(
                        "Anthropic returned %d, retrying (%d/%d)",
                        exc.response.status_code,
                        attempt + 1,
                        _MAX_RETRIES,
                    )
                    last_exc = exc
                    await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
                    continue
                body = exc.response.text
                raise ProviderError(provider=_PROVIDER_NAME, reason=f"{exc.response.status_code}: {body}") from exc
            except Exception as exc:
                raise ProviderError(provider=_PROVIDER_NAME, reason=str(exc)) from exc
        raise ProviderError(provider=_PROVIDER_NAME, reason=str(last_exc)) from last_exc

    async def generate_stream(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream tokens from the Anthropic API as they are generated.

        Retries on 5xx errors only before any tokens have been yielded.
        Once streaming begins, errors are raised immediately.
        """
        payload = self._build_payload(prompt, context, history, **kwargs)
        payload["stream"] = True
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                async with self._client.stream("POST", _API_URL, headers=self._build_headers(), json=payload) as resp:
                    if resp.status_code >= 500 and attempt < _MAX_RETRIES:
                        await resp.aread()
                        logger.warning(
                            "Anthropic returned %d on stream, retrying (%d/%d)",
                            resp.status_code,
                            attempt + 1,
                            _MAX_RETRIES,
                        )
                        last_exc = ProviderError(
                            provider=_PROVIDER_NAME,
                            reason=f"{resp.status_code}: {resp.text}",
                        )
                        await asyncio.sleep(_RETRY_DELAY * (attempt + 1))
                        continue
                    if resp.status_code != 200:
                        await resp.aread()
                        raise ProviderError(
                            provider=_PROVIDER_NAME,
                            reason=f"{resp.status_code}: {resp.text}",
                        )
                    # Once we start yielding, no more retries.
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            event = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        if event.get("type") == "content_block_delta":
                            delta = event.get("delta", {})
                            if delta.get("type") == "text_delta":
                                yield delta["text"]
                    return
            except ProviderError:
                raise
            except Exception as exc:
                raise ProviderError(provider=_PROVIDER_NAME, reason=str(exc)) from exc
        raise last_exc or ProviderError(provider=_PROVIDER_NAME, reason="Max retries exceeded")
