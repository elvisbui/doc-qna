"""Application configuration via Pydantic BaseSettings."""

from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All environment variables for the doc-qna backend."""

    # LLM provider selection
    LLM_PROVIDER: Literal["ollama", "anthropic", "openai", "cloudflare"] = "ollama"

    # Embedding provider selection
    EMBEDDING_PROVIDER: Literal["openai", "ollama", "cloudflare", "chromadb"] = "ollama"

    # Chunking strategy: "fixed" (sliding window) or "semantic" (paragraph-based)
    CHUNKING_STRATEGY: Literal["fixed", "semantic"] = "fixed"

    # Retrieval strategy: "vector" (embedding only) or "hybrid" (vector + BM25 with RRF)
    RETRIEVAL_STRATEGY: Literal["vector", "hybrid"] = "vector"

    # Ollama (self-hosted)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_AUTO_PULL: bool = True

    # Anthropic (hosted)
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_AUTH_TOKEN: str | None = None

    # OpenAI (hosted)
    OPENAI_API_KEY: str | None = None

    # Cloudflare Workers AI (free tier)
    CLOUDFLARE_ACCOUNT_ID: str | None = None
    CLOUDFLARE_API_TOKEN: str | None = None
    CLOUDFLARE_LLM_MODEL: str = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"
    CLOUDFLARE_EMBEDDING_MODEL: str = "@cf/baai/bge-base-en-v1.5"

    # Embedding model
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Ollama embedding model (used when EMBEDDING_PROVIDER=ollama)
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # ChromaDB mode: "embedded" uses PersistentClient locally, "client" connects to a remote server
    CHROMA_MODE: Literal["embedded", "client"] = "embedded"

    # ChromaDB persistence directory (used in embedded mode)
    CHROMA_PERSIST_DIR: str = "./chroma_data"

    # ChromaDB server connection (used in client mode)
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001

    # Uploaded files directory
    UPLOAD_DIR: str = "./uploads"

    # Logging
    LOG_LEVEL: str = "INFO"

    # API key authentication (comma-separated; empty = auth disabled)
    API_KEYS: str = ""

    # Embedding cache size (for query embeddings)
    EMBEDDING_CACHE_SIZE: int = 128

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = False
    RATE_LIMIT_REQUESTS: int = 60  # max requests per window
    RATE_LIMIT_WINDOW: int = 60  # window in seconds

    # Plugin directory
    PLUGINS_DIR: str = "plugins"

    # Knowledge packs directory
    PACKS_DIR: str = "../packs"

    # Custom system prompt (empty = use default SYSTEM_PROMPT_TEMPLATE)
    SYSTEM_PROMPT: str = ""

    # LLM generation parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_TOP_P: float = 1.0
    LLM_MAX_TOKENS: int = 2048

    # Multi-user document isolation (opt-in)
    MULTI_USER_ENABLED: bool = False

    # CORS allowed origins
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://localhost:8000",
    ]

    model_config = SettingsConfigDict(env_file=".env")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        """Parse CORS origins from a comma-separated string or list.

        Args:
            v: Either a comma-separated string of origins or an already
                parsed list.

        Returns:
            A list of origin strings with whitespace stripped and empty
            entries removed.
        """
        if isinstance(v, str):
            return [o for origin in v.split(",") if (o := origin.strip())]
        return v


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance.

    Uses ``lru_cache`` so the settings are read from environment variables
    and ``.env`` only once, then reused for the lifetime of the process.

    Returns:
        The singleton ``Settings`` instance.
    """
    return Settings()
