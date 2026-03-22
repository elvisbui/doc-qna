---
sidebar_position: 2
---

# Embeddable Chat Widget

doc-qna includes a standalone chat widget that can be embedded on any website with a single `<script>` tag.

## Usage

Add this to any HTML page:

```html
<script
  src="https://your-doc-qna-instance.com/doc-qna-widget.js"
  data-api-url="https://your-doc-qna-instance.com"
  data-api-key="your-api-key"
></script>
```

This renders a floating chat bubble in the bottom-right corner. Clicking it opens a mini chat interface that communicates with your doc-qna backend via the `/api/chat` SSE endpoint.

## Attributes

| Attribute | Required | Description |
|-----------|----------|-------------|
| `data-api-url` | Yes | Base URL of your doc-qna instance |
| `data-api-key` | No | API key for authentication (if enabled) |

## Features

- Floating bubble with expand/collapse
- Streaming SSE responses
- Shadow DOM for complete style isolation (no CSS conflicts)
- Self-contained — no external stylesheets needed
- Lightweight: ~64KB gzipped

## Building the Widget

```bash
cd frontend
npm run build:widget
```

This uses a separate Vite config (`vite.widget.config.ts`) to produce a UMD bundle:

```
frontend/dist/doc-qna-widget.js
```

## Technical Details

- **Build format**: UMD (Universal Module Definition) via Vite library mode
- **Style isolation**: Shadow DOM encapsulates all widget styles
- **CSS**: Inline styles (no TailwindCSS dependency)
- **SSE parsing**: Self-contained implementation (no main app imports)
- **Bundle size**: ~204KB uncompressed, ~64KB gzipped
