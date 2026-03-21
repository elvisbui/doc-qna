---
sidebar_position: 2
---

# Quickstart

Once you have doc-qna [installed](/docs/getting-started/installation), here's how to use it.

## 1. Upload a Document

Navigate to the **Documents** tab and either:
- Click the upload area to browse for a file, or
- Drag and drop a file onto the upload zone

Supported formats: **PDF**, **DOCX**, **Markdown**, **Plain Text**

The document will be parsed, chunked, embedded, and indexed automatically. You can track processing status in the document list.

## 2. Ask a Question

Switch to the **Chat** tab and type a question about your uploaded document. For example:

> "What are the main points discussed in this document?"

The system will:
1. Embed your query
2. Search for relevant chunks (vector search or hybrid)
3. Send the context + question to the LLM
4. Stream back an answer with inline citations

## 3. Review Citations

Answers include **inline citation markers** like [1], [2] that correspond to source passages. Click a citation badge to scroll to the matching source in the **Citation Panel** on the right.

## 4. Install a Knowledge Pack (Optional)

Go to the **Packs** tab to browse pre-built document collections. Click **Install** to load a pack's documents into the system with suggested starter queries.

## 5. Configure Providers (Optional)

Visit the **Settings** tab to:
- Switch LLM provider (Ollama, OpenAI, Anthropic)
- Change the embedding provider
- Select a system prompt preset
- Adjust temperature and other parameters
- Enter API keys for cloud providers

## Using the API Directly

You can also interact with doc-qna programmatically:

```bash
# Upload a document
curl -X POST http://localhost:8000/api/documents/upload \
  -F "file=@my-document.pdf"

# Ask a question (streaming SSE)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?", "history": []}'
```

See the full [API Reference](/docs/api/endpoints) for all available endpoints.
