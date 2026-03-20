"""Structured logging middleware with correlation IDs.

Provides:
- A ``contextvars.ContextVar`` that holds the current request's correlation ID.
- ``CorrelationIDMiddleware`` — ASGI middleware that generates (or reads from
  the ``X-Request-ID`` header) a UUID per request and stores it in the context
  var.  The same ID is returned in the ``X-Request-ID`` response header.
- ``JSONFormatter`` — a ``logging.Formatter`` subclass that outputs structured
  JSON log lines with ``timestamp``, ``level``, ``message``, ``request_id``,
  and ``logger`` fields.
- ``setup_logging()`` — configures the root logger with the JSON formatter at
  a given level.
"""

from __future__ import annotations

import json
import logging
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

# ---------------------------------------------------------------------------
# Correlation ID context variable
# ---------------------------------------------------------------------------

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Return the current request's correlation ID (or ``None``)."""
    return request_id_ctx.get()


# ---------------------------------------------------------------------------
# ASGI middleware
# ---------------------------------------------------------------------------


class CorrelationIDMiddleware:
    """ASGI middleware that assigns a correlation ID to every HTTP request.

    The ID is read from the incoming ``X-Request-ID`` header when present;
    otherwise a new UUID4 is generated.  It is stored in a ``ContextVar`` so
    that any code running within the request (including log formatters) can
    access it, and is added to the response as an ``X-Request-ID`` header.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # Extract or generate a request ID.
        headers: dict[bytes, bytes] = dict(scope.get("headers", []))
        incoming_id = headers.get(b"x-request-id", b"").decode("latin-1").strip()
        rid = incoming_id or str(uuid.uuid4())

        # Store in context var.
        token = request_id_ctx.set(rid)

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                response_headers.append((b"x-request-id", rid.encode("latin-1")))
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            request_id_ctx.reset(token)


# ---------------------------------------------------------------------------
# JSON log formatter
# ---------------------------------------------------------------------------


class JSONFormatter(logging.Formatter):
    """Emit each log record as a single JSON object.

    Fields: ``timestamp`` (ISO-8601 UTC), ``level``, ``message``,
    ``request_id`` (from the context var, may be ``null``), ``logger``.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "request_id": get_request_id(),
            "logger": record.name,
        }
        if record.exc_info and record.exc_info[1] is not None:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, default=str)


# ---------------------------------------------------------------------------
# Logging configuration helper
# ---------------------------------------------------------------------------


def setup_logging(level: str = "INFO") -> None:
    """Configure the root logger with the structured JSON formatter.

    Parameters
    ----------
    level:
        Log level name (e.g. ``"DEBUG"``, ``"INFO"``).  Parsed via
        ``logging.getLevelName``.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.setLevel(logging.getLevelName(level.upper()))
    # Remove any existing handlers to avoid duplicate output.
    root.handlers.clear()
    root.addHandler(handler)
