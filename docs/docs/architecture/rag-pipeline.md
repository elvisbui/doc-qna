---
sidebar_position: 2
---

# RAG Pipeline

The retrieval-augmented generation pipeline is the core of doc-qna. It transforms uploaded documents into queryable knowledge and generates cited answers.

## Ingestion Pipeline

When a document is uploaded, it goes through four stages:

### 1. Parse

The appropriate parser extracts text based on file type:

| Format | Parser | Notes |
|--------|--------|-------|
| PDF | `pypdf` | Extracts per-page text with page numbers |
| DOCX | `python-docx` | Extracts paragraph text |
| Markdown | Built-in | Reads raw text |
| Plain text | Built-in | Reads raw text |

PDF parsing preserves page boundaries, enabling page-number citations in answers.

### 2. Chunk

Text is split into overlapping chunks using one of two strategies:

- **Fixed-window** (default): splits text into chunks of `N` characters with configurable overlap
- **Semantic**: splits on paragraph boundaries, respecting natural document structure

Configured via `CHUNKING_STRATEGY` environment variable.

### 3. Embed

Each chunk is converted to a vector embedding using the configured embedding provider:

- **OpenAI** `text-embedding-3-small` (default) — high quality, low cost
- **Ollama** `nomic-embed-text` — free, local
- **ChromaDB default** — built-in, no API needed
- **Cloudflare Workers AI** — edge inference

An **embedding cache** (LRU) avoids redundant API calls for repeated queries.

### 4. Index

Embeddings and metadata (document ID, chunk position, page number) are stored in **ChromaDB**, a persistent embedded vector database.

## Retrieval

When a user asks a question, the retrieval engine finds relevant chunks:

### Vector Search
The query is embedded and compared against stored chunk embeddings using cosine similarity via ChromaDB.

### BM25 Search
A full-text search index scores chunks by term frequency (TF-IDF variant). Useful for exact keyword matches that vector search might miss.

### Hybrid Search (Reciprocal Rank Fusion)
Both vector and BM25 results are combined using **RRF**:

```
RRF_score(d) = Σ 1 / (k + rank_i(d))
```

Where `k` is a constant (default 60) and `rank_i(d)` is the rank of document `d` in result set `i`. This merges the strengths of semantic and lexical search.

Configured via `RETRIEVAL_STRATEGY=vector|hybrid`.

## Generation

Retrieved chunks are formatted as context and sent to the LLM along with the user's question and conversation history.

### Streaming
Responses are streamed via **Server-Sent Events (SSE)**, providing real-time token-by-token output. The SSE stream includes:

| Event | Data |
|-------|------|
| `message` | Text token |
| `citations` | Array of citation objects |
| `summary` | Conversation summary (when history is long) |
| `plugins` | Plugin execution trace |
| `done` | End of stream |

### Citations
The system prompt instructs the LLM to cite sources as `[1]`, `[2]`, etc. Citation objects include:
- Source text (the relevant chunk)
- Document name
- Page number (for PDFs)
- Relevance score

### Confidence & Guardrails
A confidence scoring system evaluates retrieval quality. When confidence is low, the system responds with "I don't have enough information to answer that" rather than hallucinating.

## Conversation Memory

When chat history exceeds 6 messages, older messages are **summarized by the LLM** and prepended as context. This preserves conversation continuity without exceeding token limits.

## Plugin Hooks

Plugins can intercept the pipeline at multiple points:

```
on_chunk → on_ingest → on_retrieve → on_post_retrieve → on_generate → on_post_generate
```

See [Plugins](/docs/plugins/overview) for details.
