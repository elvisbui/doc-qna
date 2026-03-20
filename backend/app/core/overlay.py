"""Settings overlay — JSON file persistence for user overrides.

Shared module used by both routers (settings) and services (generation)
to read/write the settings overlay file without circular imports.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


def overlay_path() -> Path:
    """Return the path to the settings overlay JSON file."""
    settings = get_settings()
    return Path(settings.UPLOAD_DIR).resolve().parent / "settings.json"


def load_overlay() -> dict[str, Any]:
    """Load the overlay file, returning an empty dict if it doesn't exist."""
    path = overlay_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read settings overlay %s: %s", path, exc)
        return {}


def save_overlay(data: dict[str, Any]) -> None:
    """Persist the overlay dict to disk atomically with restrictive permissions."""
    path = overlay_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(data, indent=2) + "\n"
    # Write to a temp file then atomically replace to avoid partial writes on crash.
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    try:
        tmp.chmod(0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
