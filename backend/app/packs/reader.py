"""Read, extract, and validate knowledge packs."""

from __future__ import annotations

import json
import tarfile
from typing import TYPE_CHECKING

from app.packs.models import PackManifest

if TYPE_CHECKING:
    from pathlib import Path


def read_manifest(pack_path: Path) -> PackManifest:
    """Read the manifest from a pack archive without fully extracting it.

    Args:
        pack_path: Path to a ``.tar.gz`` pack file.

    Returns:
        The parsed ``PackManifest``.

    Raises:
        FileNotFoundError: If the pack file or manifest is missing.
        ValueError: If the manifest cannot be parsed.
    """
    if not pack_path.is_file():
        raise FileNotFoundError(f"Pack file not found: {pack_path}")

    with tarfile.open(pack_path, "r:gz") as tar:
        manifest_member = _find_manifest_member(tar)
        if manifest_member is None:
            raise ValueError(f"No manifest.json found in pack: {pack_path}")

        f = tar.extractfile(manifest_member)
        if f is None:
            raise ValueError(f"Could not read manifest.json from pack: {pack_path}")

        data = json.loads(f.read())
        return PackManifest(**data)


def extract_pack(pack_path: Path, target_dir: Path) -> PackManifest:
    """Extract a pack's contents to *target_dir* and return its manifest.

    Args:
        pack_path: Path to a ``.tar.gz`` pack file.
        target_dir: Directory where contents will be extracted.

    Returns:
        The parsed ``PackManifest``.

    Raises:
        FileNotFoundError: If the pack file is missing.
        ValueError: If the manifest cannot be parsed.
    """
    if not pack_path.is_file():
        raise FileNotFoundError(f"Pack file not found: {pack_path}")

    target_dir.mkdir(parents=True, exist_ok=True)

    with tarfile.open(pack_path, "r:gz") as tar:
        # Security: filter out absolute paths and path traversals
        safe_members = _get_safe_members(tar, target_dir)
        tar.extractall(target_dir, members=safe_members, filter="data")

    # Read manifest from the extracted directory
    manifest_candidates = list(target_dir.rglob("manifest.json"))
    if not manifest_candidates:
        raise ValueError(f"No manifest.json found after extracting: {pack_path}")

    manifest_path = manifest_candidates[0]
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    return PackManifest(**data)


def validate_pack(pack_path: Path) -> list[str]:
    """Validate a pack archive and return a list of errors (empty = valid).

    Checks performed:
        1. File exists and is a valid tar.gz archive.
        2. Contains a ``manifest.json``.
        3. Manifest parses as valid ``PackManifest``.
        4. All documents listed in the manifest are present in the archive.
        5. Pack name is non-empty.

    Args:
        pack_path: Path to a ``.tar.gz`` pack file.

    Returns:
        A list of error strings.  An empty list means the pack is valid.
    """
    errors: list[str] = []

    if not pack_path.is_file():
        errors.append(f"Pack file not found: {pack_path}")
        return errors

    try:
        tar = tarfile.open(pack_path, "r:gz")  # noqa: SIM115
    except tarfile.TarError as exc:
        errors.append(f"Not a valid tar.gz archive: {exc}")
        return errors

    with tar:
        # Check for manifest
        manifest_member = _find_manifest_member(tar)
        if manifest_member is None:
            errors.append("Missing manifest.json in pack archive")
            return errors

        # Parse manifest
        f = tar.extractfile(manifest_member)
        if f is None:
            errors.append("Could not read manifest.json from archive")
            return errors

        try:
            data = json.loads(f.read())
            manifest = PackManifest(**data)
        except (json.JSONDecodeError, ValueError, TypeError, KeyError) as exc:
            errors.append(f"Invalid manifest.json: {exc}")
            return errors

        # Validate manifest fields
        if not manifest.name:
            errors.append("Pack name must not be empty")

        if not manifest.version:
            errors.append("Pack version must not be empty")

        # Check that listed documents exist in the archive
        member_names = {m.name for m in tar.getmembers()}
        for doc_rel in manifest.documents:
            # Documents are stored as <pack-name>/<relative-path>
            expected = f"{manifest.name}/{doc_rel}"
            if expected not in member_names:
                errors.append(f"Listed document missing from archive: {doc_rel}")

        # Check doc_count consistency
        if manifest.doc_count != len(manifest.documents):
            errors.append(
                f"doc_count ({manifest.doc_count}) does not match number of documents ({len(manifest.documents)})"
            )

    return errors


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_manifest_member(tar: tarfile.TarFile) -> tarfile.TarInfo | None:
    """Return the TarInfo for ``manifest.json`` inside the archive."""
    for member in tar.getmembers():
        if member.name.endswith("manifest.json") and member.isfile():
            return member
    return None


def _get_safe_members(tar: tarfile.TarFile, target_dir: Path) -> list[tarfile.TarInfo]:
    """Filter out archive members with unsafe paths (absolute or traversal)."""
    safe: list[tarfile.TarInfo] = []
    resolved_target = target_dir.resolve()
    for member in tar.getmembers():
        if member.name.startswith("/"):
            continue
        resolved = (target_dir / member.name).resolve()
        if not resolved.is_relative_to(resolved_target):
            continue
        safe.append(member)
    return safe
