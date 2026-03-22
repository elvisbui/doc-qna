"""Summarizer plugin — auto-generate a document summary on ingest."""

from __future__ import annotations

import re

from app.plugins.base import PluginBase


def _first_sentence(text: str) -> str:
    """Extract the first sentence from *text*.

    Uses a simple regex that splits on sentence-ending punctuation
    followed by whitespace or end-of-string.  Falls back to the full
    text (stripped) if no sentence boundary is found.
    """
    text = text.strip()
    if not text:
        return ""
    match = re.match(r"(.+?[.!?])(?:\s|$)", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


class SummarizerPlugin(PluginBase):
    """Auto-generate a document summary on ingest.

    The summary is built by extracting the first sentence of each chunk
    (simple extractive summarization — no LLM calls).  It is prepended
    to the chunk list so that retrieval can surface the summary when the
    user asks for an overview of a document.
    """

    name: str = "summarizer"
    description: str = "Auto-generate a document summary on ingest"

    def on_ingest(self, document_id: str, chunks: list[str]) -> list[str]:
        """Prepend an extractive summary chunk to *chunks*."""
        if not chunks:
            return chunks

        sentences = [_first_sentence(chunk) for chunk in chunks]
        # Filter out empty sentences that may result from blank chunks.
        sentences = [s for s in sentences if s]

        if not sentences:
            return chunks

        summary_text = " ".join(sentences)
        summary_chunk = f"[SUMMARY] {summary_text}"
        return [summary_chunk] + list(chunks)


def register(app: object) -> SummarizerPlugin:
    """Plugin loader convention — instantiate and return the plugin."""
    return SummarizerPlugin()
