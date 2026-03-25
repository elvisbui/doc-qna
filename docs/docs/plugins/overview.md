---
sidebar_position: 1
---

# Plugin System

doc-qna has a hook-based plugin system that lets you intercept and modify the RAG pipeline at multiple stages.

## How It Works

Plugins implement lifecycle hooks that are called at specific points in the pipeline:

```
Document Upload:
  on_chunk → on_ingest

User Query:
  on_retrieve → on_post_retrieve → on_generate → on_post_generate
```

The **PluginPipeline** dispatches events to all enabled plugins in order. Each plugin can transform the data before passing it to the next stage.

## Plugin Hooks

| Hook | When | Input → Output |
|------|------|-----------------|
| `on_chunk` | During document chunking | `(text, metadata) → text` |
| `on_ingest` | After document is split | `(doc_id, chunks) → chunks` |
| `on_retrieve` | Before embedding user query | `(query) → query` |
| `on_post_retrieve` | After retrieval, before LLM | `(query, results) → results` |
| `on_generate` | Before LLM call | `(prompt, context) → (prompt, context)` |
| `on_post_generate` | After LLM response | `(answer) → answer` |

## Managing Plugins

### Via the UI

Navigate to the **Plugins** page to:
- See all discovered plugins
- Enable/disable plugins
- Configure plugin-specific settings

### Via the API

```bash
# List plugins
curl http://localhost:8000/api/plugins

# Update plugin config
curl -X PUT http://localhost:8000/api/plugins/query_rewriter/config \
  -H "Content-Type: application/json" \
  -d '{"enabled": true, "config": {"mode": "hyde"}}'
```

## Plugin Tracing

Every hook execution is logged with timing data. The chat response includes a `plugins` SSE event showing:
- Which plugins ran
- Which hooks were called
- Execution time per hook
- Any errors

This trace is also displayed in the **Plugin Activity Panel** in the Chat page.

## Configuration

Plugins declare their configuration fields using `ConfigField`:

```python
config_fields = [
    ConfigField(
        name="mode",
        field_type="select",
        default="basic",
        label="Rewrite Mode",
        description="How to rewrite queries",
        options=["basic", "hyde"]
    ),
]
```

Field types: `string`, `number`, `boolean`, `select`

Configuration is persisted in `backend/app/plugins/registry.json`.
