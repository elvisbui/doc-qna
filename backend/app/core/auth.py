"""Shared authentication utilities.

Provides user identification logic used by both the documents and chat routers.
"""

import hashlib

from starlette.requests import Request

from app.config import Settings

_ANONYMOUS_USER_ID = "anonymous"


def resolve_user_id(request: Request, settings: Settings) -> str | None:
    """Derive a user_id from the request when multi-user isolation is enabled.

    Returns ``None`` when ``MULTI_USER_ENABLED`` is ``False`` (no filtering).
    When enabled, hashes the ``X-API-Key`` header to produce a short stable
    identifier.  Falls back to ``"anonymous"`` if no key is present.
    """
    if not settings.MULTI_USER_ENABLED:
        return None

    api_key = request.headers.get("x-api-key")
    if not api_key:
        return _ANONYMOUS_USER_ID

    return hashlib.sha256(api_key.encode()).hexdigest()[:16]
