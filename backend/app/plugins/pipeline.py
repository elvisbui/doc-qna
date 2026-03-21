"""Plugin execution pipeline — ordered hook dispatch with error isolation."""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.plugins.base import PluginBase

logger = logging.getLogger(__name__)


class PluginPipeline:
    """Dispatch lifecycle hooks to an ordered list of plugins.

    Each hook is called in sequence; the output of one plugin feeds into the
    next.  If a plugin raises an exception the error is logged and the plugin
    is skipped — the pipeline never crashes.

    An execution trace is recorded for every hook invocation so that callers
    (or a debug UI) can inspect timing and ordering after the fact.
    """

    def __init__(self, plugins: list[PluginBase]) -> None:
        self.plugins = plugins
        self._trace: list[dict] = []

    # -- trace bookkeeping ---------------------------------------------------

    def get_trace(self) -> list[dict]:
        """Return the execution trace for the last request."""
        return list(self._trace)

    def clear_trace(self) -> None:
        """Reset the execution trace."""
        self._trace.clear()

    # -- generic dispatcher --------------------------------------------------

    def run_hook(
        self,
        hook_name: str,
        *args: Any,
        _pre_args: tuple = (),
        _post_args: tuple = (),
    ) -> Any:
        """Call *hook_name* on every enabled plugin in order.

        Each plugin is called with ``(*_pre_args, *flowing_args, *_post_args)``.
        The flowing args start as ``*args`` and are replaced by each plugin's
        return value (unpacked when it is a tuple).

        ``_pre_args`` and ``_post_args`` are context parameters passed to every
        plugin unchanged.

        Returns the final flowing result after all plugins have been applied.
        """
        result = args

        for plugin in self.plugins:
            if not plugin.enabled:
                continue

            hook = getattr(plugin, hook_name, None)
            if hook is None:
                continue

            call_args = _pre_args + result + _post_args

            start = time.perf_counter()
            try:
                value = hook(*call_args)
            except Exception:
                duration_ms = (time.perf_counter() - start) * 1000
                logger.exception(
                    "Plugin %s raised in hook %s (%.1f ms) — skipping",
                    plugin.name,
                    hook_name,
                    duration_ms,
                )
                self._trace.append(
                    {
                        "plugin": plugin.name,
                        "hook": hook_name,
                        "duration_ms": round(duration_ms, 2),
                        "error": True,
                    }
                )
                continue

            duration_ms = (time.perf_counter() - start) * 1000
            self._trace.append(
                {
                    "plugin": plugin.name,
                    "hook": hook_name,
                    "duration_ms": round(duration_ms, 2),
                    "error": False,
                }
            )

            # Normalize result for next iteration.
            result = value if isinstance(value, tuple) else (value,)

        # Unwrap single-element tuples for a nicer caller experience.
        if len(result) == 1:
            return result[0]
        return result

    # -- convenience methods -------------------------------------------------

    def run_on_chunk(self, text: str, metadata: dict) -> str:
        """Run ``on_chunk`` across all plugins.

        ``metadata`` is passed to every plugin as a fixed trailing arg.
        """
        return self.run_hook("on_chunk", text, _post_args=(metadata,))

    def run_on_ingest(self, document_id: str, chunks: list[str]) -> list[str]:
        """Run ``on_ingest`` across all plugins.

        ``document_id`` is a fixed leading arg; ``chunks`` flows through.
        """
        return self.run_hook("on_ingest", chunks, _pre_args=(document_id,))

    def run_on_retrieve(self, query: str) -> str:
        """Run ``on_retrieve`` across all plugins."""
        return self.run_hook("on_retrieve", query)

    def run_on_post_retrieve(self, query: str, results: list[dict]) -> list[dict]:
        """Run ``on_post_retrieve`` across all plugins.

        ``query`` is a fixed leading arg; ``results`` flows through.
        """
        return self.run_hook("on_post_retrieve", results, _pre_args=(query,))

    def run_on_generate(self, prompt: str, context: str) -> tuple[str, str]:
        """Run ``on_generate`` across all plugins."""
        return self.run_hook("on_generate", prompt, context)

    def run_on_post_generate(self, answer: str) -> str:
        """Run ``on_post_generate`` across all plugins."""
        return self.run_hook("on_post_generate", answer)
