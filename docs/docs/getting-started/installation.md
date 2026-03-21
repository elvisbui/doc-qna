---
sidebar_position: 1
---

# Installation

There are three ways to get doc-qna running: Docker (recommended), automated setup script, or manual setup.

## Prerequisites

- **Docker** (for Docker method): Docker Desktop or Docker Engine + Docker Compose
- **Python 3.13+** (for local method)
- **Node.js 20+** (for local method)
- **Ollama** (optional, for local LLM inference)

## Option 1: Docker (Recommended)

The fastest way to get started. This runs FastAPI + Ollama together.

```bash
git clone https://github.com/elvisbui/doc-qna.git
cd doc-qna
docker compose up --build -d
```

Pull the required models:

```bash
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

## Option 2: Setup Script

An automated script that sets up either Docker or local development:

```bash
git clone https://github.com/elvisbui/doc-qna.git
cd doc-qna
chmod +x setup.sh
./setup.sh
```

The script detects your environment and offers Docker or local setup.

## Option 3: Manual Local Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with your provider settings (see [Environment Variables](/docs/configuration/environment-variables)).

Start the backend:

```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server runs at `http://localhost:5173` and proxies API requests to the backend.

### Ollama (Optional)

If using Ollama as your LLM provider:

```bash
# Install Ollama: https://ollama.ai
ollama pull llama3.2
ollama pull nomic-embed-text
```

## Using Makefile

Common tasks are available via Make:

```bash
make setup          # Automated local setup
make setup-docker   # Docker setup
make dev            # Start backend dev server
make test           # Run all tests
make build          # Build frontend + Docker image
make lint           # Lint Python + TypeScript
make typecheck      # Type-check Python + TypeScript
```

## Verify Installation

Once running, verify the health endpoint:

```bash
curl http://localhost:8000/api/health
```

You should see:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": { ... }
}
```
