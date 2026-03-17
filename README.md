# doc-qna

**Upload documents. Ask questions. Get cited answers.**

A Retrieval-Augmented Generation (RAG) system that lets users upload documents and ask natural-language questions, receiving accurate, cited answers grounded in their own data -- not hallucinated internet responses. Runs entirely on your own hardware with Ollama at zero cost, or connects to OpenAI / Anthropic APIs.

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

### Option 1: One-command setup (recommended)

```bash
git clone https://github.com/elvisbui/doc-qna.git
cd doc-qna
./setup.sh          # local dev setup (Python + Node + Ollama)
# or
./setup.sh docker   # Docker setup (everything in containers)
```

### Option 2: Docker Compose

```bash
git clone https://github.com/elvisbui/doc-qna.git
cd doc-qna
docker compose up --build -d
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text
```

Open [http://localhost:8000](http://localhost:8000) in your browser.

### Option 3: Local development

**Prerequisites:** Python 3.13+, Node.js 20+, [Ollama](https://ollama.com) (or OpenAI/Anthropic API keys)

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

```bash
# Frontend (separate terminal)
cd frontend
npm install
npm run dev
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
| `OPENAI_API_KEY` | -- | Required when using OpenAI |
| `ANTHROPIC_API_KEY` | -- | Required when using Anthropic |
| `CHROMA_PERSIST_DIR` | `./chroma_data` | ChromaDB storage path |
| `UPLOAD_DIR` | `./uploads` | Uploaded files directory |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:8000` | Allowed CORS origins |

See [`backend/.env.example`](backend/.env.example) for the full reference.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/documents/upload` | Upload a document |
| `GET` | `/api/documents` | List all documents |
| `GET` | `/api/documents/{id}/status` | Check processing status |
| `DELETE` | `/api/documents/{id}` | Delete a document |
| `POST` | `/api/chat` | Send a query (streaming SSE) |
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
│   │   ├── routers/               # API route handlers (chat, documents)
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   └── services/              # Business logic (ingestion, retrieval, generation)
│   ├── tests/                     # pytest test suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/            # React components
│   │   ├── hooks/                 # Custom React hooks
│   │   ├── pages/                 # Page-level components
│   │   ├── lib/                   # Utilities
│   │   └── types/                 # TypeScript type definitions
│   └── package.json
├── docker-compose.yml
├── Dockerfile
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
