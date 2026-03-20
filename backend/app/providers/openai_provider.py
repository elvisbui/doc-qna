"""OpenAI LLM provider implementation using the openai v1.x SDK."""

from collections.abc import AsyncIterator
from typing import Any

import openai
from openai import AsyncOpenAI

from app.core.constants import MAX_RESPONSE_TOKENS, SYSTEM_PROMPT_TEMPLATE
from app.core.exceptions import ProviderError

_PROVIDER_NAME = "openai"


class OpenAIProvider:
    """LLM provider backed by OpenAI's chat completions API.

    Satisfies the ``LLMProvider`` protocol defined in ``providers/base.py``
    via structural subtyping — no inheritance required.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str | None = None) -> None:
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._model = model

    def _build_messages(
        self,
        prompt: str,
        context: str,
        history: list[dict] | None = None,
        system_prompt: str | None = None,
    ) -> list[dict]:
        """Build the messages list with system prompt, history, and current query."""
        effective_prompt = system_prompt if system_prompt else SYSTEM_PROMPT_TEMPLATE
        messages: list[dict] = [
            {"role": "system", "content": effective_prompt.replace("{context}", context)},
        ]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})
        return messages

    async def generate(self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any) -> str:
        """Generate a complete response for *prompt* grounded in *context*."""
        system_prompt = kwargs.get("system_prompt")
        create_kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": kwargs.get("max_tokens", MAX_RESPONSE_TOKENS),
            "messages": self._build_messages(prompt, context, history, system_prompt=system_prompt),
        }
        if "temperature" in kwargs:
            create_kwargs["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            create_kwargs["top_p"] = kwargs["top_p"]
        try:
            response = await self._client.chat.completions.create(**create_kwargs)
            if not response.choices:
                return ""
            content = response.choices[0].message.content
            return content or ""
        except openai.APIError as exc:
            raise ProviderError(provider=_PROVIDER_NAME, reason=str(exc)) from exc

    async def generate_stream(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        """Stream response tokens for *prompt* grounded in *context*."""
        system_prompt = kwargs.get("system_prompt")
        create_kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": kwargs.get("max_tokens", MAX_RESPONSE_TOKENS),
            "messages": self._build_messages(prompt, context, history, system_prompt=system_prompt),
            "stream": True,
        }
        if "temperature" in kwargs:
            create_kwargs["temperature"] = kwargs["temperature"]
        if "top_p" in kwargs:
            create_kwargs["top_p"] = kwargs["top_p"]
        try:
            stream = await self._client.chat.completions.create(**create_kwargs)
            async for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except openai.APIError as exc:
            raise ProviderError(provider=_PROVIDER_NAME, reason=str(exc)) from exc
