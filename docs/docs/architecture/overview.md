---
sidebar_position: 1
---

# Architecture Overview

doc-qna follows a clean layered architecture with clear separation between HTTP handling, business logic, and external integrations.

## System Diagram

```
┌──────────────────────────────────────────────────┐
│                   FRONTEND                       │
│          React + Vite + TypeScript               │
│                                                  │
│  ┌────────────┐ ┌──────────────────────────────┐ │
│  │  Document   │ │         Chat Interface       │ │
│  │  Upload &   │ │  w/ Streaming + Inline       │ │
│  │  Manager    │ │  Citations                   │ │
│  └────────────┘ └──────────────────────────────┘ │
└──────────────────┬───────────────────────────────┘
                   │ Built → served as static files
┌──────────────────▼───────────────────────────────┐
│              BACKEND (Python + FastAPI)           │
│                                                  │
│  ┌───────────┐ ┌────────────┐ ┌──────────────┐  │
│  │ Ingestion │ │ Retrieval  │ │ Generation   │  │
│  │ Pipeline  │ │ Engine     │ │ + Citations  │  │
│  │           │ │            │ │ + Guardrails │  │
│  │ • Parse   │ │ • Vector   │ │              │  │
│  │ • Chunk   │ │   search   │ │ • Streaming  │  │
│  │ • Embed   │ │ • BM25     │ │ • "I don't   │  │
│  │ • Index   │ │ • Hybrid   │ │    know"     │  │
│  └───────────┘ └────────────┘ └──────────────┘  │
│                                                  │
│  ┌───────────┐ ┌──────────────┐                  │
│  │ ChromaDB  │ │ Provider     │                  │
│  │ (vectors) │ │ Wrappers     │                  │
│  │           │ │ (Protocols)  │                  │
│  └───────────┘ └──────────────┘                  │
└──────────────────────────────────────────────────┘
```

## Layer Responsibilities

### Routers (`app/routers/`)
- HTTP request/response handling
- Input validation via Pydantic schemas
- No business logic — delegates to services

### Services (`app/services/`)
- Pure Python business logic
- No FastAPI imports
- Orchestrates providers, parsers, and data stores
- Independently testable

### Providers (`app/providers/`)
- Protocol-based wrappers for external APIs
- `LLMProvider` and `EmbeddingProvider` Protocols defined in `base.py`
- Implementations: Ollama, OpenAI, Anthropic, Cloudflare
- Singleton pattern — created once at startup

### Core (`app/core/`)
- Domain models (`Document`, `DocumentChunk`, `Citation`)
- Constants (system prompts, defaults)
- Custom exceptions
- Authentication logic

### Middleware (`app/middleware/`)
- API key authentication
- Rate limiting
- Structured logging with correlation IDs
- Request timing

## Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | React 19 + Vite + TypeScript + TailwindCSS v4 | Lightweight, fast builds, single-page app |
| Backend | Python 3.13 + FastAPI | Async, typed, auto-generated OpenAPI |
| Vector DB | ChromaDB (embedded) | Free, in-process, persistent |
| Embeddings | OpenAI text-embedding-3-small (default) | High quality, $0.02/1M tokens |
| LLM | Ollama / OpenAI / Anthropic | Provider flexibility |
| Parsers | pypdf, python-docx | PDF, DOCX, MD, TXT |

## Design Decisions

### No LangChain in Core
The RAG pipeline uses thin Protocol-based provider wrappers instead of LangChain. This keeps the codebase simple, removes a heavy dependency, and demonstrates understanding of RAG internals.

### Single-Server Model
The React frontend is built by Vite and served as static files from FastAPI. No separate frontend server in production — simplifies deployment and eliminates CORS configuration.

### Vector-First, Hybrid Later
The MVP shipped with vector-only retrieval. BM25 and hybrid search (Reciprocal Rank Fusion) were added in v1.1, showing iterative improvement.
