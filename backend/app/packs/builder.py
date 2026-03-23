"""Build a knowledge pack (.tar.gz) from a set of documents."""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.packs.models import PackManifest, SuggestedQueries


def build_pack(
    name: str,
    version: str,
    description: str,
    doc_paths: list[Path],
    output_dir: Path,
    *,
    author: str = "",
    license: str = "",
    suggested_queries: list[str] | None = None,
) -> Path:
    """Create a ``.tar.gz`` knowledge pack from source documents.

    Args:
        name: Short identifier for the pack.
        version: Semantic version string.
        description: Human-readable description.
        doc_paths: List of paths to source document files.
        output_dir: Directory where the archive will be written.
        author: Author or organisation name.
        license: SPDX licence identifier.
        suggested_queries: Optional list of starter questions.

    Returns:
        Path to the created ``.tar.gz`` file.

    Raises:
        FileNotFoundError: If any document path does not exist.
        ValueError: If *name* is empty or *doc_paths* is empty.
    """
    if not name:
        raise ValueError("Pack name must not be empty")
    if not doc_paths:
        raise ValueError("At least one document path is required")

    for p in doc_paths:
        if not p.is_file():
            raise FileNotFoundError(f"Document not found: {p}")

    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        pack_root = Path(tmp) / name
        docs_dir = pack_root / "documents"
        docs_dir.mkdir(parents=True)

        # Copy documents into the staging area
        relative_paths: list[str] = []
        for src in doc_paths:
            dest = docs_dir / src.name
            shutil.copy2(src, dest)
            relative_paths.append(f"documents/{src.name}")

        # Build manifest
        manifest = PackManifest(
            name=name,
            version=version,
            description=description,
            author=author,
            license=license,
            documents=relative_paths,
            doc_count=len(relative_paths),
            created_at=datetime.now(UTC),
        )

        manifest_path = pack_root / "manifest.json"
        manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")

        # Optional suggested queries
        if suggested_queries:
            sq = SuggestedQueries(queries=suggested_queries)
            sq_path = pack_root / "suggested_queries.json"
            sq_path.write_text(json.dumps({"queries": sq.queries}, indent=2), encoding="utf-8")

        # Create .tar.gz
        archive_name = f"{name}-{version}.tar.gz"
        archive_path = output_dir / archive_name
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(pack_root, arcname=name)

    return archive_path
