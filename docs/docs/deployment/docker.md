---
sidebar_position: 1
---

# Docker Deployment

doc-qna uses a multi-stage Dockerfile and Docker Compose to run the full stack.

## Docker Compose

The default `docker-compose.yml` runs two services:

```yaml
services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - backend/.env
    depends_on:
      ollama:
        condition: service_healthy
    volumes:
      - chroma_data:/app/chroma_data
      - uploads:/app/uploads
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: unless-stopped

volumes:
  chroma_data:
  uploads:
  ollama_data:
```

## Quick Start

```bash
# Build and start
docker compose up --build -d

# Pull LLM and embedding models
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text

# Open the app
open http://localhost:8000
```

## Multi-Stage Dockerfile

The Dockerfile uses two stages:

1. **Frontend build** (Node 22) — runs `npm ci` and `npm run build` to produce static files
2. **Runtime** (Python 3.13) — installs Python dependencies, copies the backend source and frontend build output, runs as a non-root user

```dockerfile
# Stage 1: Build frontend
FROM node:22-slim AS frontend-build
# ... npm ci && npm run build → dist/

# Stage 2: Python runtime
FROM python:3.13-slim AS runtime
# ... pip install, copy backend + frontend dist + packs
# Non-root user: appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Persistent Volumes

| Volume | Purpose |
|--------|---------|
| `chroma_data` | ChromaDB vector database |
| `uploads` | Uploaded document files |
| `ollama_data` | Downloaded Ollama models |

## Environment Variables

Configure via `backend/.env` or pass directly:

```bash
docker compose up -e LLM_PROVIDER=anthropic -e ANTHROPIC_API_KEY=sk-...
```

See [Environment Variables](/docs/configuration/environment-variables) for all options.

## Without Ollama

If using OpenAI or Anthropic instead of Ollama, you can run just the app service:

```bash
docker build -t doc-qna .
docker run -p 8000:8000 \
  -e LLM_PROVIDER=openai \
  -e OPENAI_API_KEY=sk-... \
  -e EMBEDDING_PROVIDER=openai \
  -v chroma_data:/app/chroma_data \
  -v uploads:/app/uploads \
  doc-qna
```

## Health Check

```bash
curl http://localhost:8000/api/health
```
