"""Request timing middleware.

Measures the duration of each HTTP request and:
- Logs the method, path, status code, and duration.
- Adds an ``X-Response-Time`` header to the response (value in milliseconds).
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = logging.getLogger(__name__)


class TimingMiddleware:
    """ASGI middleware that records request processing time.

    Adds an ``X-Response-Time`` response header with the elapsed time
    in milliseconds and logs the duration for every HTTP request.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_code = 0

        async def send_with_timing(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                elapsed_ms = (time.perf_counter() - start) * 1000
                status_code = message.get("status", 0)

                response_headers: list[tuple[bytes, bytes]] = list(message.get("headers", []))
                response_headers.append((b"x-response-time", f"{elapsed_ms:.1f}ms".encode("latin-1")))
                message = {**message, "headers": response_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_with_timing)
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            method = scope.get("method", "?")
            path = scope.get("path", "?")
            logger.info(
                "%s %s %d completed in %.1fms",
                method,
                path,
                status_code,
                elapsed_ms,
            )
