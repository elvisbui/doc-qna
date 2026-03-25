---
sidebar_position: 3
---

# Creating Plugins

You can extend doc-qna by writing custom plugins that hook into the RAG pipeline.

## Plugin Structure

Create a new Python file in `backend/app/plugins/`:

```python
# backend/app/plugins/my_plugin.py

from backend.app.plugins.base import PluginBase, ConfigField


class MyPlugin(PluginBase):
    """A custom plugin that modifies queries."""

    name = "my_plugin"
    description = "Enhances queries with domain-specific context"
    version = "1.0.0"

    config_fields = [
        ConfigField(
            name="domain",
            field_type="string",
            default="general",
            label="Domain",
            description="Domain context to add to queries",
        ),
        ConfigField(
            name="enabled_hooks",
            field_type="select",
            default="retrieve",
            label="Active Hook",
            options=["retrieve", "generate", "both"],
        ),
    ]

    async def on_retrieve(self, query: str) -> str:
        """Modify the query before embedding and retrieval."""
        domain = self.get_config("domain", "general")
        return f"[{domain}] {query}"

    async def on_post_retrieve(self, query: str, results: list[dict]) -> list[dict]:
        """Filter or re-rank results after retrieval."""
        # Example: filter out low-confidence results
        return [r for r in results if r.get("score", 0) > 0.5]

    async def on_generate(self, prompt: str, context: str) -> tuple[str, str]:
        """Modify prompt or context before LLM call."""
        enhanced_context = f"Domain: {self.get_config('domain')}\n\n{context}"
        return prompt, enhanced_context

    async def on_post_generate(self, answer: str) -> str:
        """Transform the LLM's answer before returning."""
        return answer
```

## Available Hooks

Override any of these async methods in your plugin class:

```python
async def on_chunk(self, text: str, metadata: dict) -> str:
    """Called during document chunking. Return modified chunk text."""

async def on_ingest(self, document_id: str, chunks: list[str]) -> list[str]:
    """Called after document splitting. Return modified chunks list."""

async def on_retrieve(self, query: str) -> str:
    """Called before query embedding. Return modified query."""

async def on_post_retrieve(self, query: str, results: list[dict]) -> list[dict]:
    """Called after retrieval. Return filtered/re-ranked results."""

async def on_generate(self, prompt: str, context: str) -> tuple[str, str]:
    """Called before LLM. Return modified (prompt, context)."""

async def on_post_generate(self, answer: str) -> str:
    """Called after LLM. Return modified answer."""
```

You only need to implement the hooks you want to use — unimplemented hooks pass data through unchanged.

## Configuration Fields

Define `config_fields` to expose configurable options in the UI:

```python
ConfigField(
    name="threshold",        # Config key
    field_type="number",     # string | number | boolean | select
    default=0.5,             # Default value
    label="Score Threshold", # UI label
    description="Minimum score to keep results",
    options=None,            # For "select" type: list of choices
)
```

Access config values in hooks:

```python
threshold = self.get_config("threshold", 0.5)
```

## Plugin Discovery

Plugins are automatically discovered by the loader from the plugins directory. No manual registration needed — just create the file and restart the server.

The plugin will appear in the **Plugins** page in the UI, where users can enable it and configure its settings.

## Testing Plugins

```python
# backend/tests/test_my_plugin.py
import pytest
from backend.app.plugins.my_plugin import MyPlugin


@pytest.fixture
def plugin():
    return MyPlugin()


@pytest.mark.asyncio
async def test_on_retrieve(plugin):
    result = await plugin.on_retrieve("what is RAG?")
    assert "[general]" in result


@pytest.mark.asyncio
async def test_on_post_retrieve_filters(plugin):
    results = [
        {"text": "good", "score": 0.8},
        {"text": "bad", "score": 0.3},
    ]
    filtered = await plugin.on_post_retrieve("query", results)
    assert len(filtered) == 1
```
