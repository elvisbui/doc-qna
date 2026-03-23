#!/usr/bin/env python3
"""Validate a knowledge pack archive.

Usage:
    python scripts/validate_pack.py <path_to_pack.tar.gz>

Exit codes:
    0 — pack is valid
    1 — validation errors found
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI colour helpers (no external dependencies)
# ---------------------------------------------------------------------------

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _green(text: str) -> str:
    return f"{GREEN}{text}{RESET}"


def _red(text: str) -> str:
    return f"{RED}{text}{RESET}"


def _yellow(text: str) -> str:
    return f"{YELLOW}{text}{RESET}"


def _bold(text: str) -> str:
    return f"{BOLD}{text}{RESET}"


# ---------------------------------------------------------------------------
# Ensure the backend package is importable
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_BACKEND_DIR = _PROJECT_ROOT / "backend"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))


# ---------------------------------------------------------------------------
# Main logic
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate a doc-qna knowledge pack (.tar.gz).",
    )
    parser.add_argument(
        "pack_path",
        type=Path,
        help="Path to the .tar.gz pack file to validate.",
    )
    args = parser.parse_args(argv)

    pack_path: Path = args.pack_path.resolve()

    print(_bold(f"Validating pack: {pack_path}\n"))

    if not pack_path.exists():
        print(_red(f"  ERROR: File does not exist: {pack_path}"))
        return 1

    # Import here so path setup above takes effect first.
    from app.packs.reader import validate_pack  # noqa: E402

    errors = validate_pack(pack_path)

    if errors:
        print(_red(f"  FAILED — {len(errors)} error(s) found:\n"))
        for err in errors:
            print(f"    {_red('x')} {err}")
        print()
        return 1

    print(_green("  PASSED — pack is valid."))
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
