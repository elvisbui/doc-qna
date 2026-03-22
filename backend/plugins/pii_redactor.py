"""PII Redactor plugin — strips/masks sensitive data from chunks."""

from __future__ import annotations

import re

from app.plugins.base import PluginBase

# ---------------------------------------------------------------------------
# Compiled regex patterns for common PII types
# ---------------------------------------------------------------------------

# Order matters: credit-card check before generic digit sequences.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # SSN  (XXX-XX-XXXX)
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN]"),
    # Credit card: 16 digits with optional spaces or dashes (4-4-4-4)
    (
        re.compile(r"\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b"),
        "[CREDIT_CARD]",
    ),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[EMAIL]"),
    # US phone numbers — covers (xxx) xxx-xxxx, xxx-xxx-xxxx, xxx.xxx.xxxx,
    # xxx xxx xxxx, +1xxxxxxxxxx, etc.
    (
        re.compile(
            r"(?<!\d)"  # not preceded by digit
            r"(?:\+?1[\s\-.]?)?"  # optional country code
            r"(?:\(\d{3}\)|\d{3})"  # area code
            r"[\s\-.]?"  # separator
            r"\d{3}"  # exchange
            r"[\s\-.]?"  # separator
            r"\d{4}"  # subscriber
            r"(?!\d)"  # not followed by digit
        ),
        "[PHONE]",
    ),
    # IPv4 addresses
    (
        re.compile(
            r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
            r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b"
        ),
        "[IP_ADDRESS]",
    ),
]


class PIIRedactorPlugin(PluginBase):
    """Strip/mask sensitive data from chunks."""

    name: str = "pii_redactor"
    description: str = "Strip/mask sensitive data from chunks"

    def on_chunk(self, text: str, metadata: dict) -> str:
        """Replace detected PII with placeholder tokens."""
        for pattern, replacement in _PATTERNS:
            text = pattern.sub(replacement, text)
        return text


# ---------------------------------------------------------------------------
# Registration helper expected by the plugin loader
# ---------------------------------------------------------------------------


def register(app):  # noqa: ANN001, ARG001
    """Return an instance of the PII redactor plugin."""
    return PIIRedactorPlugin()
