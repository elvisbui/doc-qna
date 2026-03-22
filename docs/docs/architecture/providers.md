---
sidebar_position: 3
---

# Provider System

doc-qna uses Python `Protocol` classes to define provider interfaces, enabling easy swapping of LLM and embedding backends without changing business logic.

## Protocol Definitions

Providers implement two Protocols defined in `backend/app/providers/base.py`:

### LLMProvider

```python
class LLMProvider(Protocol):
    async def generate(self, prompt: str, **kwargs) -> str:
        """Generate a complete response."""
        ...

    async def generate_stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream response tokens."""
        ...
```

### EmbeddingProvider

```python
class EmbeddingProvider(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Convert texts to vector embeddings."""
        ...
```

## Available LLM Providers

### Ollama (Self-Hosted)

Free, local inference using open-source models.

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_AUTO_PULL=true
```

Features:
- Automatic model pulling on startup
- Health checks
- No API key required

### OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

### Anthropic

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

### Cloudflare Workers AI

```bash
LLM_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...
CLOUDFLARE_LLM_MODEL=@cf/meta/llama-3.3-70b-instruct-fp8-fast
```

## Available Embedding Providers

| Provider | Model | Config |
|----------|-------|--------|
| **OpenAI** (default) | `text-embedding-3-small` | `EMBEDDING_PROVIDER=openai` |
| **Ollama** | `nomic-embed-text` | `EMBEDDING_PROVIDER=ollama` |
| **ChromaDB** | Default embedder | `EMBEDDING_PROVIDER=chromadb` |
| **Cloudflare** | `bge-base-en-v1.5` | `EMBEDDING_PROVIDER=cloudflare` |

## Provider Selection at Runtime

Providers can be switched from the **Settings** page in the UI without restarting the server. The settings API updates the active provider configuration on the fly.

## Adding a New Provider

1. Create a new file in `backend/app/providers/` (e.g., `my_provider.py`)
2. Implement the `LLMProvider` or `EmbeddingProvider` Protocol
3. Register it in the provider factory (`embedder.py` or similar)
4. Add configuration variables to `config.py`

No base class inheritance needed — just match the Protocol's method signatures and you're done.
