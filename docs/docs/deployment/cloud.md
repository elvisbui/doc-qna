---
sidebar_position: 2
---

# Cloud Deployment

doc-qna can be deployed to various cloud platforms. The project includes configuration files for Railway and Fly.io.

## Railway

The `railway.json` file configures Railway deployment:

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

Set environment variables in the Railway dashboard:
- `LLM_PROVIDER=openai` (or `anthropic`)
- `OPENAI_API_KEY=sk-...`
- `EMBEDDING_PROVIDER=openai`

Estimated cost: **$5-10/month**

## Fly.io

The `fly.toml` configures Fly.io deployment:

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and deploy
fly auth login
fly launch
fly deploy
```

Set secrets:

```bash
fly secrets set LLM_PROVIDER=openai
fly secrets set OPENAI_API_KEY=sk-...
fly secrets set EMBEDDING_PROVIDER=openai
```

## Cost Estimates

| Component | Cost |
|-----------|------|
| Self-hosted (Docker + Ollama) | **Free** |
| Railway or Fly.io hosting | ~$5-10/month |
| ChromaDB (embedded) | Free |
| OpenAI embeddings | ~$0.02 per 1M tokens |
| LLM (Anthropic/OpenAI) | ~$0.0025 per query |
| **Total (hosted demo)** | **$5-15/month** |

## Production Considerations

### Persistent Storage
Ensure ChromaDB data and uploads are on persistent volumes. Both Railway and Fly.io support persistent storage.

### API Keys
Use the platform's secrets management for API keys — never commit them to the repository.

### Rate Limiting
Enable rate limiting in production:

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=60
```

### Authentication
Set API keys to require authentication:

```bash
API_KEYS=key1,key2,key3
```

### CORS
Update `CORS_ORIGINS` to match your production domain:

```bash
CORS_ORIGINS=https://your-domain.com
```
