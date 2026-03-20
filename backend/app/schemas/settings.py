"""API request/response schemas for settings endpoints."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import to_camel


class SettingsResponse(BaseModel):
    """Current runtime settings (GET response)."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    embedding_provider: str
    embedding_model: str
    chunking_strategy: str
    retrieval_strategy: str
    chunk_size: int
    chunk_overlap: int
    log_level: str
    has_openai_key: bool
    has_anthropic_key: bool
    has_cloudflare_token: bool
    openai_key_hint: str
    anthropic_key_hint: str
    cloudflare_key_hint: str
    system_prompt: str
    llm_temperature: float
    llm_top_p: float
    llm_max_tokens: int


class SettingsUpdateRequest(BaseModel):
    """Partial update payload for PUT /api/settings.

    All fields are optional — only provided fields are updated.
    API keys are intentionally excluded for security.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    llm_provider: Literal["ollama", "anthropic", "openai", "cloudflare"] | None = None
    ollama_model: str | None = Field(None, min_length=1, max_length=200)
    embedding_provider: Literal["openai", "ollama", "cloudflare", "chromadb"] | None = None
    embedding_model: str | None = Field(None, min_length=1, max_length=200)
    chunking_strategy: Literal["fixed", "semantic"] | None = None
    retrieval_strategy: Literal["vector", "hybrid"] | None = None
    chunk_size: int | None = Field(None, ge=100, le=10000)
    chunk_overlap: int | None = Field(None, ge=0, le=5000)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = None
    system_prompt: str | None = Field(None, max_length=10000)
    llm_temperature: float | None = Field(None, ge=0.0, le=2.0)
    llm_top_p: float | None = Field(None, ge=0.0, le=1.0)
    llm_max_tokens: int | None = Field(None, ge=128, le=16384)


class ApiKeyUpdateRequest(BaseModel):
    """Body for POST /api/settings/api-keys.

    At least one key must be provided. Values are stored in the overlay file.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    openai_api_key: str | None = Field(None, min_length=1)
    anthropic_api_key: str | None = Field(None, min_length=1)
    cloudflare_api_token: str | None = Field(None, min_length=1)
    cloudflare_account_id: str | None = Field(None, min_length=1)


class PromptPreset(BaseModel):
    """A built-in system prompt preset."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
    )

    id: str
    name: str
    description: str
    system_prompt: str


class ConnectionTestRequest(BaseModel):
    """Body for POST /api/settings/test-connection."""

    provider: Literal["ollama", "openai", "anthropic", "cloudflare"]
    config: dict = Field(default_factory=dict)


class ConnectionTestResponse(BaseModel):
    """Response for POST /api/settings/test-connection."""

    status: Literal["ok", "error"]
    message: str
