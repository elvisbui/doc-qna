# doc-qna

**Upload documents. Ask questions. Get cited answers.**

[![CI](https://github.com/elvisbui/doc-qna/actions/workflows/ci.yml/badge.svg)](https://github.com/elvisbui/doc-qna/actions/workflows/ci.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Live Demo](https://img.shields.io/badge/demo-doc--qna.elvisbui.dev-blue)](https://doc-qna.elvisbui.dev)

A Retrieval-Augmented Generation (RAG) system that lets users upload documents and ask natural-language questions, receiving accurate, cited answers grounded in their own data -- not hallucinated internet responses. Runs entirely on your own hardware with Ollama at zero cost, or connects to OpenAI / Anthropic APIs.

**[Try the live demo →](https://doc-qna.elvisbui.dev)**

<!-- screenshot -->

---

## Features

- **Document Upload and Management** -- PDF, DOCX, Markdown, and plain text
- **Conversational Q&A with Citations** -- answers reference specific passages with clickable inline citations
- **Streaming Responses** -- real-time Server-Sent Events for a responsive chat experience
- **Multiple LLM Providers** -- swap between Ollama (free, local), OpenAI, or Anthropic via a single env var
- **Configurable Embeddings** -- choose OpenAI or Ollama embeddings independently of the LLM provider
- **Hybrid Search** -- vector similarity + BM25 full-text search for better retrieval
- **Confidence-Based Guardrails** -- the system abstains when retrieval confidence is too low instead of guessing
- **Plugin System** -- hook-based architecture with built-in plugins (query rewriter, PII redactor, re-ranker, summarizer)
- **Knowledge Packs** -- installable document collections with suggested queries
- **Observability Dashboard** -- query latency, relevance scores, and error tracking
- **Conversation Memory** -- LLM-powered summarization of long chat histories
- **Embeddable Widget** -- drop a `<script>` tag on any page to add a chat widget
- **Dark Mode** -- system-aware with manual toggle
- **Self-Hostable** -- Docker Compose + Ollama, no API keys required
- **No LangChain** -- thin Protocol-based provider wrappers; all RAG internals are visible, not hidden behind framework abstractions

---

## Architecture

```
Upload ──> Parse ──> Chunk ──> Embed ──> Index (ChromaDB)
                                              │
Query  ──> Embed ──> Vector Search ───────────┘
                         │
                         v
                 Retrieve top-k chunks
                         │
                         v
              Generate answer (LLM) + cite sources
                         │
                         v
              Stream response via SSE
```

The frontend is built with Vite and served as static files from FastAPI (single-server model -- no separate frontend server, no CORS issues in production).

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 6, TypeScript, Tailwind CSS v4 |
| Backend | Python 3.13, FastAPI |
| Vector DB | ChromaDB (embedded mode, no separate server) |
| Embeddings | OpenAI `text-embedding-3-small` or Ollama `nomic-embed-text` |
| LLM Providers | Ollama, OpenAI, Anthropic |
| Document Parsing | pypdf, python-docx |
| Deployment | Docker Compose |

---

## Quick Start

> Don't want to install anything? **[Try the live demo](https://doc-qna.elvisbui.dev)** -- upload a document and start asking questions in seconds.

### Option 1: One-command setup (recommended)

```bash
git clone https://github.com/elvisbui/doc-qna.git
cd doc-qna
./setup.sh          # local dev setup (Python + Node + Ollama)
# or
./setup.sh docker   # Docker setup (everything in containers)
```

The setup script installs all dependencies, creates `.env`, and pulls Ollama models automatically.

### Option 2: Docker Compose (manual)

```bash
git clone https://github.com/elvisbui/doc-qna.git
cd doc-qna
docker compose up --build -d
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Option 3: Local development (manual)

**Prerequisites:** Python 3.13+, Node.js 20+, [Ollama](https://ollama.com) (or OpenAI/Anthropic API keys)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"     # installs all deps + makes 'doc-qna' CLI available
cp .env.example .env        # edit as needed
uvicorn app.main:app --reload
```

```bash
# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

The Vite dev server starts at [http://localhost:5173](http://localhost:5173) and proxies `/api` requests to the backend.

For production, the frontend is built (`npm run build`) and served as static files from FastAPI -- no separate frontend server needed.

### Useful commands

```bash
make setup          # local setup (Python + Node + Ollama)
make setup-docker   # Docker setup
make test           # run all tests
make build          # build frontend for production
make up             # docker compose up
make down           # docker compose down
```

---

## Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure:

| Variable | Default | Description |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | LLM backend: `ollama`, `openai`, or `anthropic` |
| `EMBEDDING_PROVIDER` | `ollama` | Embedding backend: `openai` or `ollama` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama chat model |
| `OLLAMA_EMBEDDING_MODEL` | `nomic-embed-text` | Ollama embedding model (when `EMBEDDING_PROVIDER=ollama`) |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI embedding model (when `EMBEDDING_PROVIDER=openai`) |
| `OPENAI_API_KEY` | -- | Required when using OpenAI as LLM or embedding provider |
| `ANTHROPIC_API_KEY` | -- | Required when using Anthropic as LLM provider |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB storage path |
| `UPLOAD_DIR` | `./uploads` | Uploaded files directory |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8000` | Allowed CORS origins (comma-separated) |

See [`backend/.env.example`](backend/.env.example) for the full reference.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload a document (returns document ID) |
| `GET` | `/api/documents` | List all documents with metadata |
| `GET` | `/api/documents/{id}/status` | Check document processing status |
| `DELETE` | `/api/documents/{id}` | Delete a document and its chunks |
| `POST` | `/api/chat` | Send a query; returns streaming SSE response with citations |
| `GET` | `/api/health` | Health check |

---

## Project Structure

```
doc-qna/
├── backend/
│   ├── app/
│   │   ├── config.py              # Pydantic BaseSettings
│   │   ├── main.py                # FastAPI application entry point
│   │   ├── core/                  # Domain models, constants, exceptions
│   │   ├── parsers/               # PDF, DOCX, Markdown parsers
│   │   ├── providers/             # LLM + embedding provider wrappers (Protocol-based)
│   │   ├── routers/               # API route handlers (chat, documents, settings, plugins, packs)
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── services/              # Business logic (ingestion, retrieval, generation, metrics)
│   │   └── plugins/               # Hook-based plugin system
│   ├── tests/                     # pytest test suite
│   ├── eval/                      # RAG evaluation pipeline (DeepEval)
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/            # React components (chat, documents, settings, UI)
│   │   ├── hooks/                 # Custom React hooks
│   │   ├── pages/                 # Page-level components
│   │   ├── widget/                # Embeddable chat widget (Shadow DOM)
│   │   ├── lib/                   # API client, SSE parser, utilities
│   │   └── types/                 # TypeScript type definitions
│   └── package.json
├── docs/                          # Docusaurus documentation site
├── packs/                         # Knowledge pack registry + sample packs
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── README.md
```

---

## Running Tests

```bash
cd backend
pytest
```

Tests use pytest with async support (`pytest-asyncio`). Test files live in `backend/tests/` and mirror the `app/` structure.

---

## License

[MIT](LICENSE) -- Copyright (c) Elvis Bui
