---
sidebar_position: 1
---

# Environment Variables

All backend configuration is managed through environment variables, loaded via Pydantic `BaseSettings` in `backend/app/config.py`. Copy `.env.example` to `.env` to get started.

## LLM Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | Active LLM provider: `ollama`, `openai`, `anthropic`, `cloudflare` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `OLLAMA_AUTO_PULL` | `true` | Auto-download model if not present |
| `OPENAI_API_KEY` | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | — | Anthropic API key |
| `CLOUDFLARE_ACCOUNT_ID` | — | Cloudflare account ID |
| `CLOUDFLARE_API_TOKEN` | — | Cloudflare Workers AI token |
| `CLOUDFLARE_LLM_MODEL` | `@cf/meta/llama-3.3-70b-instruct-fp8-fast` | Cloudflare LLM model |

## Embedding Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `EMBEDDING_PROVIDER` | `openai` | Active embedder: `openai`, `ollama`, `chromadb`, `cloudflare` |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `CLOUDFLARE_EMBEDDING_MODEL` | `@cf/baai/bge-base-en-v1.5` | Cloudflare embedding model |
| `EMBEDDING_CACHE_SIZE` | `128` | LRU cache size for query embeddings |

## Chunking & Retrieval

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNKING_STRATEGY` | `fixed` | Chunking strategy: `fixed`, `semantic` |
| `RETRIEVAL_STRATEGY` | `vector` | Retrieval strategy: `vector`, `hybrid` |

## ChromaDB

| Variable | Default | Description |
|----------|---------|-------------|
| `CHROMA_MODE` | `embedded` | ChromaDB mode: `embedded`, `client` |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | Directory for persistent storage |
| `CHROMA_HOST` | `localhost` | ChromaDB server host (client mode) |
| `CHROMA_PORT` | `8001` | ChromaDB server port (client mode) |

## LLM Parameters

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_TEMPERATURE` | `0.7` | Sampling temperature |
| `LLM_TOP_P` | `1.0` | Top-p (nucleus) sampling |
| `LLM_MAX_TOKENS` | `2048` | Maximum response tokens |
| `SYSTEM_PROMPT` | (built-in) | Custom system prompt (empty = default) |

## Security

| Variable | Default | Description |
|----------|---------|-------------|
| `API_KEYS` | — | Comma-separated API keys (empty = auth disabled) |
| `RATE_LIMIT_ENABLED` | `false` | Enable rate limiting |
| `RATE_LIMIT_REQUESTS` | `60` | Max requests per window |
| `RATE_LIMIT_WINDOW` | `60` | Rate limit window in seconds |
| `MULTI_USER_ENABLED` | `false` | Enable per-user document isolation |

## File Storage

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_DIR` | `./uploads` | Document upload directory |
| `PLUGINS_DIR` | `plugins` | Plugin directory |
| `PACKS_DIR` | `../packs` | Knowledge packs directory |

## Server

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8000` | Allowed CORS origins |
