---
sidebar_position: 2
---

# Streaming SSE

The `/api/chat` endpoint returns responses as a **Server-Sent Events (SSE)** stream, enabling real-time token-by-token rendering in the frontend.

## Event Format

Each event follows the SSE specification:

```
event: <event_type>
data: <json_payload>

```

## Event Types

### `message`

A text token from the LLM response. Concatenate all message events to build the full answer.

```
event: message
data: {"token": "The"}

event: message
data: {"token": " main"}

event: message
data: {"token": " finding"}
```

### `citations`

An array of citation objects for the answer. Sent once, typically before `done`.

```
event: citations
data: [
  {
    "text": "The study found that...",
    "documentName": "report.pdf",
    "pageNumber": 12,
    "score": 0.89
  },
  {
    "text": "Additionally, results show...",
    "documentName": "report.pdf",
    "pageNumber": 15,
    "score": 0.82
  }
]
```

### `summary`

Emitted when conversation history was summarized (long conversations). Contains the generated summary.

```
event: summary
data: {"summary": "Previous discussion covered methodology and data collection..."}
```

### `plugins`

Plugin execution trace showing which hooks ran and their timing.

```
event: plugins
data: [
  {"plugin": "query_rewriter", "hook": "on_retrieve", "duration_ms": 45},
  {"plugin": "reranker", "hook": "on_post_retrieve", "duration_ms": 120}
]
```

### `done`

Marks the end of the stream.

```
event: done
data: {}
```

## Frontend Consumption

The frontend `useChat` hook handles SSE parsing:

```typescript
const response = await fetch('/api/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ query, history }),
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  // Parse SSE events from chunk
  // Update UI state per event type
}
```

## Inline Citations

The system prompt instructs the LLM to use `[1]`, `[2]`, etc. markers in its response text. The frontend parses these markers and renders them as clickable superscript badges that scroll to the corresponding citation in the Citation Panel.

## Error Handling

If an error occurs during streaming, the server sends:

```
event: error
data: {"message": "Failed to generate response"}
```

The frontend should display the error message and stop reading the stream.
