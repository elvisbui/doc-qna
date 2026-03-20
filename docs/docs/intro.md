---
sidebar_position: 1
slug: /
---

# Introduction

**doc-qna** is a production-ready RAG (Retrieval-Augmented Generation) system that lets users upload documents and ask natural language questions, receiving accurate, cited answers grounded in their own data.

## Why doc-qna?

- **RAG is the most in-demand AI engineering pattern** — 60% of production LLM applications use it
- **Full-stack**: document ingestion, vector search, LLM generation, streaming UI
- **Provider-agnostic**: swap between Ollama (free, local), OpenAI, or Anthropic
- **Self-hostable**: single `docker compose up` runs everything locally
- **Extensible**: plugin system, knowledge packs, embeddable widget

## Key Features

| Feature | Description |
|---------|-------------|
| **Document Upload** | PDF, DOCX, Markdown, plain text |
| **Hybrid Search** | Vector similarity + BM25 full-text with Reciprocal Rank Fusion |
| **Streaming Answers** | Real-time SSE responses with inline citations |
| **Multiple LLM Providers** | Ollama, OpenAI, Anthropic via Protocol-based wrappers |
| **Plugin System** | Hook-based architecture with built-in summarizer, query rewriter, PII redactor, re-ranker |
| **Knowledge Packs** | Bundled document collections installable from the UI |
| **Embeddable Widget** | Drop-in `<script>` tag for any website |
| **Observability** | Metrics dashboard with latency, relevance, and error tracking |
| **Dark Mode** | Full dark/light theme support |
| **Conversation Memory** | Intelligent history summarization |

## Architecture at a Glance

```
Upload → Parse → Chunk → Embed → Index
                                    ↓
              Query → Retrieve → Generate → Stream
```

The frontend is built with React and served as static files from FastAPI — a single-server model that simplifies deployment and eliminates CORS issues.

## Quick Links

- [Installation](/docs/getting-started/installation) — get up and running
- [Architecture](/docs/architecture/overview) — understand how it works
- [API Reference](/docs/api/endpoints) — backend endpoints
- [Plugins](/docs/plugins/overview) — extend functionality
- [Deployment](/docs/deployment/docker) — production deployment
