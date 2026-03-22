---
sidebar_position: 3
---

# Embedding Providers

Embedding providers convert text into vector representations for semantic search. doc-qna supports several embedding backends.

## OpenAI (Default)

```bash
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
OPENAI_API_KEY=sk-...
```

High-quality embeddings at $0.02 per 1M tokens. Recommended for production use.

## Ollama

```bash
EMBEDDING_PROVIDER=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://localhost:11434
```

Free, local embeddings. Pull the model first:

```bash
ollama pull nomic-embed-text
```

## ChromaDB Default

```bash
EMBEDDING_PROVIDER=chromadb
```

Uses ChromaDB's built-in default embedding function. No API key required — good for quick testing.

## Cloudflare Workers AI

```bash
EMBEDDING_PROVIDER=cloudflare
CLOUDFLARE_EMBEDDING_MODEL=@cf/baai/bge-base-en-v1.5
CLOUDFLARE_ACCOUNT_ID=...
CLOUDFLARE_API_TOKEN=...
```

## Embedding Cache

Query embeddings are cached in memory using an LRU cache to avoid redundant API calls:

```bash
EMBEDDING_CACHE_SIZE=128  # Number of cached embeddings
```

Cache statistics are logged at server shutdown.

:::caution Important
When switching embedding providers, existing document embeddings become incompatible. You'll need to re-upload and re-index your documents to use the new embedding space.
:::
