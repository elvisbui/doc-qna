---
sidebar_position: 1
---

# API Endpoints

All API routes use the `/api/` prefix. The backend auto-generates OpenAPI documentation at `/docs` (Swagger UI) and `/redoc`.

## Documents

### Upload Document

```http
POST /api/documents/upload
Content-Type: multipart/form-data
```

Upload a file for processing (parse, chunk, embed, index).

**Request:** `file` field with a PDF, DOCX, MD, or TXT file.

**Response (202):**
```json
{
  "documentId": "abc123",
  "filename": "report.pdf",
  "status": "processing"
}
```

### List Documents

```http
GET /api/documents
```

Returns all documents with metadata and processing status.

**Response (200):**
```json
{
  "documents": [
    {
      "id": "abc123",
      "filename": "report.pdf",
      "status": "ready",
      "chunkCount": 42,
      "uploadedAt": "2026-03-15T10:30:00Z"
    }
  ],
  "total": 1
}
```

### Document Status

```http
GET /api/documents/{id}/status
```

Check the processing status of a specific document.

**Response (200):**
```json
{
  "status": "ready",
  "errorMessage": null
}
```

Status values: `processing`, `ready`, `error`

### Delete Document

```http
DELETE /api/documents/{id}
```

Deletes a document, its chunks, and embeddings from ChromaDB.

**Response (200):**
```json
{
  "success": true,
  "message": "Document deleted"
}
```

## Chat

### Send Query

```http
POST /api/chat
Content-Type: application/json
```

Send a question and receive a streaming SSE response with citations.

**Request:**
```json
{
  "query": "What are the main findings?",
  "history": [
    {"role": "user", "content": "Tell me about the methodology"},
    {"role": "assistant", "content": "The study uses..."}
  ]
}
```

**Response:** Server-Sent Events stream. See [Streaming SSE](/docs/api/streaming-sse) for format details.

## Settings

### Get Settings

```http
GET /api/settings
```

Returns current provider and parameter configuration.

### Update Settings

```http
PUT /api/settings
Content-Type: application/json
```

**Request:**
```json
{
  "llmProvider": "openai",
  "embeddingProvider": "openai",
  "temperature": 0.7,
  "systemPrompt": "You are a helpful assistant..."
}
```

### Get Prompt Presets

```http
GET /api/settings/presets
```

Returns available system prompt presets.

**Response (200):**
```json
{
  "presets": [
    {"name": "General", "prompt": "You are a helpful..."},
    {"name": "Customer Support", "prompt": "You are a customer..."},
    {"name": "Legal Research", "prompt": "You are a legal..."},
    {"name": "Study Assistant", "prompt": "You are a study..."},
    {"name": "Technical Docs", "prompt": "You are a technical..."}
  ]
}
```

## Plugins

### List Plugins

```http
GET /api/plugins
```

Returns all discovered plugins with metadata, enabled status, and configuration.

### Update Plugin Config

```http
PUT /api/plugins/{name}/config
Content-Type: application/json
```

Enable/disable a plugin or update its configuration values.

## Knowledge Packs

### List Packs

```http
GET /api/packs
```

Returns available and installed knowledge packs.

### Install Pack

```http
POST /api/packs/install
Content-Type: application/json
```

**Request:**
```json
{
  "packId": "python-basics"
}
```

## Metrics

### Get Summary

```http
GET /api/metrics/summary
```

Aggregated metrics: queries per day, avg latency, avg relevance, error rate, P50/P95 latency.

### Get Recent Requests

```http
GET /api/metrics/recent
```

Last 100 requests with per-request latency, relevance, and token counts.

## Health

### Health Check

```http
GET /api/health
```

**Response (200):**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "chromadb": "connected",
    "ollama": "connected"
  }
}
```

## Authentication

When `API_KEYS` is set, all endpoints require an `Authorization` header:

```http
Authorization: Bearer your-api-key
```

Or as a query parameter: `?api_key=your-api-key`
