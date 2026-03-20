"""API key authentication middleware.

Checks for X-API-Key header on /api/ routes (except /api/health).
When API_KEYS setting is empty, authentication is disabled (open access).
"""

import json
import logging
import secrets

from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings
from app.middleware import get_asgi_header

logger = logging.getLogger(__name__)


class APIKeyMiddleware:
    """ASGI middleware that enforces API key authentication on /api/ routes."""

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the middleware and parse configured API keys.

        Args:
            app: The wrapped ASGI application.
        """
        self.app = app
        settings = get_settings()
        # Parse comma-separated keys, stripping whitespace, ignoring empty strings.
        self.valid_keys: list[str] = [k.strip() for k in settings.API_KEYS.split(",") if k.strip()]
        if self.valid_keys:
            logger.info("API key authentication enabled (%d key(s) configured)", len(self.valid_keys))
        else:
            logger.info("API key authentication disabled (API_KEYS is empty)")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Process an ASGI request, enforcing API key auth on /api/ routes.

        Non-HTTP scopes, non-API paths, and ``/api/health`` are passed
        through without authentication. When auth is enabled, missing or
        invalid keys receive a 401 JSON response.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        # Skip auth if no keys configured (open access / dev mode).
        if not self.valid_keys:
            await self.app(scope, receive, send)
            return

        # Only protect /api/ routes, and exempt /api/health.
        if not path.startswith("/api/") or path == "/api/health":
            await self.app(scope, receive, send)
            return

        # Extract X-API-Key header from raw ASGI headers.
        api_key = get_asgi_header(scope, b"x-api-key")

        if api_key is None:
            await self._send_401(send, "Missing API key. Provide it via the X-API-Key header.")
            return

        if not self._is_valid_key(api_key):
            await self._send_401(send, "Invalid API key.")
            return

        await self.app(scope, receive, send)

    def _is_valid_key(self, provided_key: str) -> bool:
        """Check if the provided key matches any configured valid key.

        Uses ``secrets.compare_digest`` for timing-safe comparison to
        prevent timing side-channel attacks.

        Args:
            provided_key: The API key value from the request header.

        Returns:
            ``True`` if the key matches any configured valid key,
            ``False`` otherwise.
        """
        return any(secrets.compare_digest(provided_key, valid_key) for valid_key in self.valid_keys)

    @staticmethod
    async def _send_401(send: Send, message: str) -> None:
        """Send a 401 Unauthorized JSON error response.

        Args:
            send: The ASGI send callable for the current connection.
            message: Human-readable error message to include in the
                JSON response body.
        """
        body = json.dumps(
            {
                "error": {
                    "type": "authentication_error",
                    "message": message,
                    "detail": None,
                }
            }
        ).encode("utf-8")

        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body,
            }
        )
