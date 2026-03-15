"""Application configuration via Pydantic BaseSettings."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All environment variables for the doc-qna backend."""

    LLM_PROVIDER: Literal["ollama", "anthropic", "openai"] = "ollama"
    EMBEDDING_PROVIDER: Literal["openai", "ollama", "cloudflare", "chromadb"] = "ollama"
    CHUNKING_STRATEGY: Literal["fixed", "semantic"] = "fixed"
    RETRIEVAL_STRATEGY: Literal["vector", "hybrid"] = "vector"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_AUTO_PULL: bool = True

    ANTHROPIC_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None

    EMBEDDING_MODEL: str = "text-embedding-3-small"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    CHROMA_PERSIST_DIR: str = "./chroma_data"
    UPLOAD_DIR: str = "./uploads"
    LOG_LEVEL: str = "INFO"

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [o for origin in v.split(",") if (o := origin.strip())]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
