"""Middleware package."""

from starlette.types import Scope


def get_asgi_header(scope: Scope, header_name: bytes) -> str | None:
    """Extract a header value from the ASGI scope (case-insensitive)."""
    headers: list[tuple[bytes, bytes]] = scope.get("headers", [])
    for name, value in headers:
        if name.lower() == header_name:
            return value.decode("latin-1")
    return None
