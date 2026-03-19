# Cloud Deployment Guide

This guide covers deploying doc-qna to **Fly.io** and **Railway**.

Both platforms build from the project's multi-stage `Dockerfile` and require at least one API key for an LLM/embedding provider.

---

## Prerequisites

- A working Docker build (`docker build -t doc-qna .` should succeed)
- At least one provider API key (OpenAI, Anthropic, or a self-hosted Ollama URL)

---

## Fly.io

### 1. Install the CLI

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
```

### 2. Launch the app (first time)

```bash
fly launch --no-deploy          # creates app from fly.toml
fly volumes create doc_qna_data --size 1 --region sjc
fly deploy
```

The volume (`doc_qna_data`) persists ChromaDB data and uploaded files across deploys.

### 3. Set secrets

```bash
fly secrets set \
  LLM_PROVIDER=openai \
  EMBEDDING_PROVIDER=openai \
  OPENAI_API_KEY=sk-... \
  CORS_ORIGINS="https://doc-qna.fly.dev"
```

For Anthropic:

```bash
fly secrets set \
  LLM_PROVIDER=anthropic \
  EMBEDDING_PROVIDER=openai \
  ANTHROPIC_API_KEY=sk-ant-... \
  OPENAI_API_KEY=sk-...
```

### 4. Verify

```bash
fly status
curl https://doc-qna.fly.dev/api/health
```

### 5. View logs

```bash
fly logs
```

### Configuration reference

See `fly.toml` in the project root. Key settings:

| Setting | Value | Notes |
|---------|-------|-------|
| Memory | 256 MB | Minimum; increase for large document sets |
| Region | sjc | Change `primary_region` as needed |
| Volume | 1 GB | Increase with `fly volumes extend` |
| Health check | `/api/health` | Polls every 15 seconds |

---

## Railway

### 1. Install the CLI (optional — Railway also has a web dashboard)

```bash
npm install -g @railway/cli
railway login
```

### 2. Deploy

From the project root:

```bash
railway init
railway up
```

Or connect your GitHub repo via the Railway dashboard — it will auto-detect the `Dockerfile` and `railway.json`.

### 3. Set environment variables

In the Railway dashboard (or via CLI):

```bash
railway variables set LLM_PROVIDER=openai
railway variables set EMBEDDING_PROVIDER=openai
railway variables set OPENAI_API_KEY=sk-...
railway variables set CORS_ORIGINS=https://your-app.up.railway.app
```

Railway automatically sets the `PORT` variable. The start command in `railway.json` uses `$PORT` so the app binds to the correct port.

### 4. Persistent storage

Railway provides ephemeral disks by default. For persistent ChromaDB data, attach a **Railway Volume** via the dashboard:

1. Go to your service settings.
2. Add a volume mounted at `/data`.
3. Set environment variables:
   - `CHROMA_PERSIST_DIR=/data/chroma_data`
   - `UPLOAD_DIR=/data/uploads`

### 5. Verify

```bash
curl https://your-app.up.railway.app/api/health
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LLM_PROVIDER` | No | `ollama` | `ollama`, `openai`, or `anthropic` |
| `EMBEDDING_PROVIDER` | No | `ollama` | `openai` or `ollama` |
| `OPENAI_API_KEY` | If using OpenAI | — | OpenAI API key |
| `ANTHROPIC_API_KEY` | If using Anthropic | — | Anthropic API key |
| `OLLAMA_BASE_URL` | If using Ollama | `http://localhost:11434` | Ollama server URL |
| `CHROMA_PERSIST_DIR` | No | `./chroma_data` | ChromaDB storage path |
| `UPLOAD_DIR` | No | `./uploads` | Uploaded files path |
| `CORS_ORIGINS` | Recommended | localhost only | Comma-separated allowed origins |
| `LOG_LEVEL` | No | `INFO` | Python log level |

---

## Troubleshooting

- **Health check failing**: Check logs for startup errors. Ensure API keys are set if using a hosted provider.
- **ChromaDB data lost on redeploy**: Verify a persistent volume is mounted and `CHROMA_PERSIST_DIR` points to it.
- **CORS errors in browser**: Set `CORS_ORIGINS` to your deployed app's URL.
- **Out of memory**: Increase memory allocation (Fly: update `fly.toml` `[[vm]]` section; Railway: adjust in dashboard).
