"""Rate limiting middleware.

Simple in-memory sliding window rate limiter. Tracks requests per client IP
(or per API key when authentication is enabled). Exempt: /api/health.

Enable via RATE_LIMIT_ENABLED=true in environment / .env.
"""

import hashlib
import json
import logging
import threading
import time
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.middleware import get_asgi_header

logger = logging.getLogger(__name__)


class RateLimitMiddleware:
    """ASGI middleware that enforces per-client request rate limits."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        settings = get_settings()
        self.max_requests: int = settings.RATE_LIMIT_REQUESTS
        self.window: int = settings.RATE_LIMIT_WINDOW

        # {client_key: [timestamp, ...]}
        self._requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

        logger.info(
            "Rate limiting enabled: %d requests per %d seconds",
            self.max_requests,
            self.window,
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        # Exempt health endpoint from rate limiting.
        if path == "/api/health":
            await self.app(scope, receive, send)
            return

        client_key = self._identify_client(scope)
        now = time.time()

        with self._lock:
            self._cleanup(client_key, now)
            timestamps = self._requests.setdefault(client_key, [])
            remaining = self.max_requests - len(timestamps)
            reset_at = int(now) + self.window

            if remaining <= 0:
                # Find earliest expiry to compute Retry-After.
                earliest = timestamps[0] if timestamps else now
                retry_after = int(earliest + self.window - now) + 1
                if retry_after < 1:
                    retry_after = 1

                await self._send_429(send, retry_after, reset_at)
                return

            # Record this request.
            timestamps.append(now)
            remaining -= 1

        # Inject rate limit headers into the downstream response.
        await self._proxy_with_headers(scope, receive, send, remaining, reset_at)

    def _identify_client(self, scope: Scope) -> str:
        """Return the client identifier: API key hash if present, otherwise IP."""
        api_key = get_asgi_header(scope, b"x-api-key")
        if api_key:
            hashed = hashlib.sha256(api_key.encode()).hexdigest()[:12]
            return f"key:{hashed}"

        # Fall back to client IP from ASGI scope.
        client = scope.get("client")
        if client:
            return f"ip:{client[0]}"
        return "ip:unknown"

    def _cleanup(self, client_key: str, now: float) -> None:
        """Remove timestamps outside the current window for a given client."""
        if client_key not in self._requests:
            return
        cutoff = now - self.window
        self._requests[client_key] = [ts for ts in self._requests[client_key] if ts > cutoff]
        # Remove entry entirely if empty to avoid unbounded dict growth.
        if not self._requests[client_key]:
            del self._requests[client_key]

    async def _proxy_with_headers(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        remaining: int,
        reset_at: int,
    ) -> None:
        """Forward the request to the app, injecting rate-limit headers."""
        rate_limit_headers: list[tuple[bytes, bytes]] = [
            (b"x-ratelimit-limit", str(self.max_requests).encode()),
            (b"x-ratelimit-remaining", str(remaining).encode()),
            (b"x-ratelimit-reset", str(reset_at).encode()),
        ]

        async def send_with_headers(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                existing = list(message.get("headers", []))
                existing.extend(rate_limit_headers)
                message = {**message, "headers": existing}
            await send(message)

        await self.app(scope, receive, send_with_headers)

    @staticmethod
    async def _send_429(send: Send, retry_after: int, reset_at: int) -> None:
        """Send a 429 Too Many Requests JSON error response."""
        body = json.dumps(
            {
                "error": {
                    "type": "rate_limit_error",
                    "message": "Rate limit exceeded. Please retry later.",
                    "detail": None,
                }
            }
        ).encode("utf-8")

        await send(
            {
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"retry-after", str(retry_after).encode()),
                    (b"x-ratelimit-limit", b"0"),
                    (b"x-ratelimit-remaining", b"0"),
                    (b"x-ratelimit-reset", str(reset_at).encode()),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
