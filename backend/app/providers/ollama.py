"""Ollama LLM provider implementation.

Uses httpx.AsyncClient to communicate with a local Ollama instance
via its HTTP API. Satisfies the LLMProvider protocol defined in
providers/base.py through structural subtyping.
"""

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.config import get_settings
from app.core.constants import MAX_RESPONSE_TOKENS, SYSTEM_PROMPT_TEMPLATE
from app.core.exceptions import ProviderError
from app.providers.ollama_utils import ensure_model_available

_PROVIDER_NAME = "ollama"


class OllamaProvider:
    """LLM provider that calls a local Ollama server.

    Satisfies the ``LLMProvider`` protocol without inheriting from it.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
    ) -> None:
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

    def _build_messages(
        self,
        prompt: str,
        context: str,
        history: list[dict] | None = None,
        system_prompt: str | None = None,
    ) -> list[dict]:
        """Build the messages list for the Ollama chat API."""
        effective_prompt = system_prompt if system_prompt else SYSTEM_PROMPT_TEMPLATE
        messages: list[dict] = [
            {"role": "system", "content": effective_prompt.replace("{context}", context)},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any) -> str:
        """Generate a complete response from Ollama.

        Args:
            prompt: The user's question or instruction.
            context: Retrieved document chunks to ground the response.
            history: Optional conversation history as a list of message dicts.

        Returns:
            The generated response text.

        Raises:
            ProviderError: If the Ollama server is unreachable or returns
                an error.
        """
        await self._ensure_model()
        system_prompt = kwargs.get("system_prompt")
        messages = self._build_messages(prompt, context, history, system_prompt=system_prompt)
        options: dict[str, Any] = {
            "num_predict": kwargs.get("max_tokens", MAX_RESPONSE_TOKENS),
        }
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            options["top_p"] = kwargs["top_p"]
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        try:
            response = await self._client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
        except httpx.ConnectError as exc:
            raise ProviderError(
                provider=_PROVIDER_NAME,
                reason=f"Cannot connect to Ollama at {self._base_url}: {exc}",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                provider=_PROVIDER_NAME,
                reason=f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}",
            ) from exc
        except (httpx.HTTPError, KeyError, json.JSONDecodeError) as exc:
            raise ProviderError(
                provider=_PROVIDER_NAME,
                reason=f"Unexpected error from Ollama: {exc}",
            ) from exc

    async def generate_stream(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream tokens from Ollama as they are generated.

        Uses the Ollama chat API with messages format, which supports
        multi-turn conversation history.

        Args:
            prompt: The user's question or instruction.
            context: Retrieved document chunks to ground the response.
            history: Optional conversation history as a list of message dicts.

        Yields:
            Individual tokens as they arrive from Ollama.

        Raises:
            ProviderError: If the Ollama server is unreachable or returns
                an error.
        """
        await self._ensure_model()
        system_prompt = kwargs.get("system_prompt")
        messages = self._build_messages(prompt, context, history, system_prompt=system_prompt)
        options: dict[str, Any] = {
            "num_predict": kwargs.get("max_tokens", MAX_RESPONSE_TOKENS),
        }
        if "temperature" in kwargs:
            options["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            options["top_p"] = kwargs["top_p"]
        payload = {
            "model": self._model,
            "messages": messages,
            "stream": True,
            "options": options,
        }

        try:
            async with self._client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = data.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if data.get("done", False):
                        break
        except httpx.ConnectError as exc:
            raise ProviderError(
                provider=_PROVIDER_NAME,
                reason=f"Cannot connect to Ollama at {self._base_url}: {exc}",
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                provider=_PROVIDER_NAME,
                reason=f"Ollama returned HTTP {exc.response.status_code}: {exc.response.text}",
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                provider=_PROVIDER_NAME,
                reason=f"Unexpected error from Ollama: {exc}",
            ) from exc
