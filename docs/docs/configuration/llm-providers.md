---
sidebar_position: 2
---

# LLM Providers

doc-qna supports multiple LLM providers. You can switch providers via environment variables or the Settings page in the UI.

## Ollama (Default)

Free, self-hosted inference using open-source models. Recommended for development and privacy-sensitive deployments.

```bash
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_AUTO_PULL=true
```

### Setup

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull a model
ollama pull llama3.2
```

### Recommended Models

| Model | Size | Best For |
|-------|------|----------|
| `llama3.2` | 3B | Fast responses, lower resource usage |
| `llama3.1` | 8B | Better quality, moderate resources |
| `mistral` | 7B | Good balance of speed and quality |
| `mixtral` | 8x7B | Highest quality, requires more RAM |

### Auto-Pull

When `OLLAMA_AUTO_PULL=true`, doc-qna automatically downloads the configured model on startup if it's not already present.

## OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

Uses the OpenAI Chat Completions API. The model is configurable from the Settings page.

## Anthropic

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Uses Claude models via the Anthropic Messages API.

## Cloudflare Workers AI

```bash
LLM_PROVIDER=cloudflare
CLOUDFLARE_ACCOUNT_ID=your-account-id
CLOUDFLARE_API_TOKEN=your-api-token
CLOUDFLARE_LLM_MODEL=@cf/meta/llama-3.3-70b-instruct-fp8-fast
```

Edge inference via Cloudflare's Workers AI platform.

## Switching Providers at Runtime

Navigate to **Settings** in the UI to change the LLM provider, model, and parameters without restarting the server. Changes take effect immediately for the next query.
