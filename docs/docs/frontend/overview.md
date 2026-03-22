---
sidebar_position: 1
---

# Frontend Overview

The doc-qna frontend is a React 19 single-page application built with Vite, TypeScript, and TailwindCSS v4. In production, it's built as static files and served directly from FastAPI.

## Pages

| Page | Description |
|------|-------------|
| **Landing** | Hero page with feature overview and quick-start instructions |
| **Chat** | Main Q&A interface with streaming responses, inline citations, and conversation memory |
| **Documents** | Upload, list, preview, and delete documents |
| **Packs** | Browse and install knowledge pack collections |
| **Plugins** | Enable, disable, and configure plugins |
| **Settings** | LLM/embedding provider selection, system prompt presets, API keys |
| **Metrics** | Observability dashboard with latency, relevance, and error charts |

## Key Components

### Chat Interface
- **MessageList** — renders streaming assistant messages with Markdown support and inline `[N]` citation badges
- **ChatInput** — text input with send button and keyboard shortcuts
- **CitationPanel** — displays source passages with highlighting and scroll-to-citation
- **CitationLink** — accessible superscript badge linking inline citations to the panel
- **SuggestedQueries** — starter questions from knowledge packs
- **ConversationSummary** — shows when older messages have been summarized
- **PluginActivityPanel** — traces plugin hook execution

### Document Management
- **FileUpload** — drag-and-drop file upload zone
- **DocumentList** — sortable, paginated list with status indicators
- **DocumentPreview** — text preview modal

### Settings
- **LLMSection** — provider dropdown, model selection, temperature slider
- **EmbeddingSection** — embedding provider and model selection
- **SystemPromptSection** — preset dropdown + custom textarea
- **ApiKeysSection** — masked input fields for API keys

## Custom Hooks

| Hook | Purpose |
|------|---------|
| `useChat` | Manages chat state, sends queries, parses SSE stream |
| `useDocuments` | Document CRUD operations |
| `useSettings` | Load/save provider settings |
| `useConversations` | Conversation history (localStorage) |
| `useDarkMode` | Dark/light theme toggle |
| `useToast` | Toast notification queue |
| `useKeyboardShortcut` | Global keyboard shortcuts |

## Development

```bash
cd frontend
npm install
npm run dev    # Vite dev server at localhost:5173
```

The dev server proxies `/api` requests to the backend at `localhost:8000`.

## Building for Production

```bash
npm run build
```

Output goes to `frontend/dist/`, which FastAPI serves as static files at the root path.
