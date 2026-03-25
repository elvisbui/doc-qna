---
sidebar_position: 2
---

# Built-in Plugins

doc-qna ships with four built-in plugins covering common RAG enhancement patterns.

## Query Rewriter

**Hook:** `on_retrieve`

Rewrites user queries to improve retrieval quality.

**Modes:**
- **Basic** — expands abbreviations, fixes typos, adds context
- **HyDE** (Hypothetical Document Embedding) — generates a hypothetical answer and uses it as the search query, improving semantic similarity matching

**Config:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `mode` | select | `basic` | Rewrite strategy: `basic` or `hyde` |

## Cross-Encoder Re-ranker

**Hook:** `on_post_retrieve`

Re-ranks retrieved chunks using a cross-encoder model for more accurate relevance scoring. Cross-encoders jointly encode the query and document, producing more accurate similarity scores than bi-encoder embeddings alone.

**Config:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `top_k` | number | `5` | Number of top results to keep after re-ranking |

## PII Redactor

**Hook:** `on_post_generate`

Scans LLM output for personally identifiable information (PII) and redacts it before returning to the user.

**Detected PII types:**
- Email addresses
- Phone numbers
- Social Security numbers
- Credit card numbers

**Config:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `redact_emails` | boolean | `true` | Redact email addresses |
| `redact_phones` | boolean | `true` | Redact phone numbers |

## Summarizer

**Hook:** `on_post_generate`

Condenses long LLM responses into shorter summaries while preserving key information and citations.

**Config:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_length` | number | `500` | Target summary length in characters |
