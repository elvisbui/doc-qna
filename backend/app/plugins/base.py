"""Plugin base class with lifecycle hooks for the doc-qna pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ConfigField:
    """Declarative description of a single plugin configuration field."""

    name: str
    field_type: str = "string"  # "string", "number", "boolean", "select"
    default: Any = ""
    label: str = ""
    description: str = ""
    options: list[str] | None = None  # for "select" type


class PluginBase:
    """Base class for doc-qna plugins.

    Subclass and override only the hooks you need.  Every hook has a
    default no-op implementation that returns its input unchanged, so
    plugins are free to be selective.

    Class attributes:
        name:        Human-readable plugin name.
        description: Short description of what the plugin does.
        config_fields: List of :class:`ConfigField` declarations.

    Instance attributes:
        enabled:     Whether the plugin is currently active (default ``True``).
        config:      Current config values (keys = field names).
    """

    name: str = "unnamed_plugin"
    description: str = ""
    config_fields: list[ConfigField] = []

    def __init__(self) -> None:
        self.enabled: bool = True
        # Initialise config from declared defaults.
        self.config: dict[str, Any] = {f.name: f.default for f in self.config_fields}

    def get_config_schema(self) -> list[dict[str, Any]]:
        """Return the config schema as a list of plain dicts."""
        result = []
        for f in self.config_fields:
            entry: dict[str, Any] = {
                "name": f.name,
                "field_type": f.field_type,
                "default": f.default,
                "label": f.label or f.name,
                "description": f.description,
            }
            if f.options is not None:
                entry["options"] = f.options
            result.append(entry)
        return result

    def update_config(self, values: dict[str, Any]) -> dict[str, Any]:
        """Update config with *values*, ignoring unknown keys.

        Returns the full config dict after update.
        """
        valid_keys = {f.name for f in self.config_fields}
        for key, value in values.items():
            if key in valid_keys:
                self.config[key] = value
        return dict(self.config)

    # -- Ingestion hooks ------------------------------------------------------

    def on_chunk(self, text: str, metadata: dict) -> str:
        """Modify a single chunk's text during ingestion.

        Called once per chunk.  Return the (possibly modified) text.
        """
        return text

    def on_ingest(self, document_id: str, chunks: list[str]) -> list[str]:
        """Modify the full list of chunks after a document has been split.

        Called once per document.  Return the (possibly modified) chunk list.
        """
        return chunks

    # -- Retrieval hooks ------------------------------------------------------

    def on_retrieve(self, query: str) -> str:
        """Modify the user query before retrieval.

        Return the (possibly rewritten) query string.
        """
        return query

    def on_post_retrieve(self, query: str, results: list[dict]) -> list[dict]:
        """Modify or rerank retrieval results after the vector search.

        Return the (possibly modified/reordered) results list.
        """
        return results

    # -- Generation hooks -----------------------------------------------------

    def on_generate(self, prompt: str, context: str) -> tuple[str, str]:
        """Modify the prompt and/or context before sending to the LLM.

        Return a ``(prompt, context)`` tuple.
        """
        return prompt, context

    def on_post_generate(self, answer: str) -> str:
        """Modify the generated answer before returning it to the user.

        Return the (possibly modified) answer string.
        """
        return answer
