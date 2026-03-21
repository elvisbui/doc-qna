---
sidebar_position: 3
---

# Project Structure

```
doc-qna/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, lifespan, static file mount
│   │   ├── config.py            # Pydantic BaseSettings (env vars)
│   │   ├── routers/             # HTTP handlers (thin validation layer)
│   │   │   ├── documents.py     # Upload, list, delete documents
│   │   │   ├── chat.py          # Streaming SSE chat
│   │   │   ├── settings.py      # Provider & prompt settings
│   │   │   ├── plugins.py       # Plugin management
│   │   │   ├── packs.py         # Knowledge pack management
│   │   │   └── metrics.py       # Observability metrics
│   │   ├── services/            # Business logic (pure Python)
│   │   │   ├── ingestion.py     # Parse → chunk → embed → index
│   │   │   ├── retrieval.py     # Vector + BM25 hybrid search
│   │   │   ├── generation.py    # LLM invocation + streaming
│   │   │   ├── chunking.py      # Fixed-window & semantic chunking
│   │   │   ├── vectorstore.py   # ChromaDB operations
│   │   │   ├── bm25.py          # BM25 full-text search
│   │   │   ├── confidence.py    # Abstention scoring
│   │   │   ├── metrics.py       # Query metrics recording
│   │   │   └── summarization.py # Conversation memory
│   │   ├── providers/           # Protocol-based LLM/embedding wrappers
│   │   │   ├── base.py          # EmbeddingProvider & LLMProvider Protocols
│   │   │   ├── ollama.py        # Ollama LLM
│   │   │   ├── anthropic_provider.py
│   │   │   ├── openai_provider.py
│   │   │   └── embedder.py      # Embedding provider router
│   │   ├── parsers/             # Document format parsers
│   │   │   ├── pdf.py           # PDF with page numbers
│   │   │   ├── docx.py          # DOCX
│   │   │   └── markdown.py      # Markdown & plain text
│   │   ├── plugins/             # Plugin system
│   │   │   ├── base.py          # PluginBase abstract class
│   │   │   ├── pipeline.py      # Hook dispatch
│   │   │   ├── loader.py        # Dynamic discovery
│   │   │   └── *.py             # Built-in plugins
│   │   ├── packs/               # Knowledge pack system
│   │   ├── middleware/           # Auth, rate limiting, logging
│   │   ├── core/                # Models, constants, exceptions
│   │   ├── schemas/             # Pydantic request/response models
│   │   └── data/                # Static data (prompt presets)
│   ├── tests/                   # pytest test suite
│   ├── eval/                    # RAG evaluation (DeepEval)
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Root component, navigation, routing
│   │   ├── pages/               # Page components
│   │   │   ├── ChatPage.tsx     # Q&A interface
│   │   │   ├── DocumentsPage.tsx
│   │   │   ├── SettingsPage.tsx
│   │   │   ├── PluginsPage.tsx
│   │   │   ├── PacksPage.tsx
│   │   │   └── MetricsPage.tsx
│   │   ├── components/          # Reusable components
│   │   ├── hooks/               # Custom React hooks
│   │   ├── lib/                 # API client, utilities
│   │   └── types/               # TypeScript type definitions
│   ├── vite.config.ts
│   ├── vite.widget.config.ts    # Embeddable widget build
│   └── package.json
│
├── packs/                       # Knowledge pack bundles
├── demo_data/                   # Sample documents
├── docker-compose.yml
├── Dockerfile                   # Multi-stage build
├── Makefile
├── .github/workflows/ci.yml
└── docs/                        # This documentation (Docusaurus)
```

## Key Design Principles

- **Routers are thin**: they handle validation and response formatting only — business logic lives in `services/`
- **Services are pure Python**: no FastAPI imports, making them testable and reusable
- **Providers use Protocols**: Python `Protocol` classes in `base.py` define the interface, enabling easy provider swaps without inheritance
- **Single-server model**: the React frontend is built and served as static files from FastAPI
