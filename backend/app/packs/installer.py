"""Knowledge pack installer — install and uninstall packs.

Handles the full lifecycle: validate, extract, ingest documents into
ChromaDB, and update the pack registry.  Uninstall removes ingested
chunks, deletes extracted pack files, and updates the registry.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.models import Document, DocumentChunk
from app.packs.reader import extract_pack, validate_pack
from app.packs.registry import PackRegistry
from app.services.ingestion import ingest_document
from app.services.vectorstore import get_default_collection

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

    from app.config import Settings
    from app.packs.models import PackManifest


async def install_pack(
    pack_path: Path,
    settings: Settings,
    registry: PackRegistry | None = None,
    collection: Collection | None = None,
) -> PackManifest:
    """Validate, extract, and ingest all documents in a knowledge pack.

    Supports both ``.tar.gz`` archives and unpacked directories.

    Args:
        pack_path: Path to a ``.tar.gz`` pack file or a pack directory.
        settings: Application settings.
        registry: Optional ``PackRegistry`` instance. If *None*, one is
            created from ``settings.PACKS_DIR``.
        collection: Optional ChromaDB collection override.

    Returns:
        The parsed ``PackManifest``.

    Raises:
        ValueError: If the pack fails validation.
    """
    if registry is None:
        registry = PackRegistry(settings.PACKS_DIR)

    if pack_path.is_dir():
        return await _install_from_directory(pack_path, settings, registry, collection)

    # Archive path — validate and extract
    errors = validate_pack(pack_path)
    if errors:
        raise ValueError(f"Invalid pack: {'; '.join(errors)}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        manifest = extract_pack(pack_path, tmp_path)
        pack_root = tmp_path / manifest.name
        return await _ingest_pack(manifest, pack_root, settings, registry, collection)


async def _install_from_directory(
    pack_dir: Path,
    settings: Settings,
    registry: PackRegistry,
    collection: Collection | None,
) -> PackManifest:
    """Install a pack from an unpacked directory."""
    import json as _json

    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"Invalid pack: No manifest.json in {pack_dir}")

    from app.packs.models import PackManifest as _PM

    data = _json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest = _PM(**data)

    return await _ingest_pack(manifest, pack_dir, settings, registry, collection)


async def _ingest_pack(
    manifest: PackManifest,
    pack_root: Path,
    settings: Settings,
    registry: PackRegistry,
    collection: Collection | None,
) -> PackManifest:
    """Shared ingestion logic for both directory and archive installs."""
    # Duplicate prevention
    installed_version = registry.get_installed_version(manifest.name)
    if installed_version == manifest.version:
        return manifest

    if collection is None:
        collection = get_default_collection(settings)

    for doc_rel in manifest.documents:
        doc_file = pack_root / doc_rel
        if not doc_file.is_file():
            continue

        document = Document(
            filename=doc_file.name,
            file_type=doc_file.suffix.lower(),
            file_size=doc_file.stat().st_size,
        )

        chunks = await ingest_document(
            file_path=doc_file,
            document=document,
            settings=settings,
            collection=collection,
        )

        await asyncio.to_thread(_tag_chunks_with_pack, collection, chunks, manifest.name)

    registry.mark_installed(manifest.name, version=manifest.version)
    return manifest


async def uninstall_pack(
    pack_name: str,
    settings: Settings,
    registry: PackRegistry | None = None,
    collection: Collection | None = None,
    delete_files: bool = False,
) -> None:
    """Remove all ingested data for a pack and mark it as uninstalled.

    Steps:
        1. Delete all chunks from ChromaDB whose metadata contains
           ``pack_name``.
        2. Optionally remove pack files from the packs directory.
        3. Mark the pack as uninstalled in the registry.

    Args:
        pack_name: The name of the pack to uninstall.
        settings: Application settings.
        registry: Optional ``PackRegistry`` instance.
        collection: Optional ChromaDB collection override.
        delete_files: If True, also remove pack files from disk.
    """
    if collection is None:
        collection = get_default_collection(settings)

    # 1. Delete all chunks tagged with this pack_name
    await asyncio.to_thread(_delete_pack_chunks, collection, pack_name)

    # 2. Optionally remove pack files from the packs directory
    if delete_files:
        packs_dir = Path(settings.PACKS_DIR)
        _remove_pack_files(packs_dir, pack_name)

    # 3. Mark as uninstalled in the registry
    if registry is None:
        registry = PackRegistry(settings.PACKS_DIR)
    registry.mark_uninstalled(pack_name)


async def upgrade_pack(
    pack_path: Path,
    settings: Settings,
    registry: PackRegistry | None = None,
    collection: Collection | None = None,
) -> PackManifest:
    """Upgrade a pack to a new version.

    If the pack is already installed at the same version the call is a
    no-op.  If a different version is installed, the old version's
    chunks are removed before the new version is ingested.  If the pack
    is not installed at all, it is simply installed.

    Args:
        pack_path: Path to the new ``.tar.gz`` pack file.
        settings: Application settings.
        registry: Optional ``PackRegistry`` instance.
        collection: Optional ChromaDB collection override.

    Returns:
        The ``PackManifest`` of the (possibly new) installed version.

    Raises:
        ValueError: If the pack fails validation.
    """
    # Validate and peek at the manifest to learn the pack name / version
    errors = validate_pack(pack_path)
    if errors:
        raise ValueError(f"Invalid pack: {'; '.join(errors)}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        manifest = extract_pack(pack_path, Path(tmp_dir))

    if registry is None:
        registry = PackRegistry(settings.PACKS_DIR)

    installed_version = registry.get_installed_version(manifest.name)

    # Already at the requested version — nothing to do
    if installed_version == manifest.version:
        return manifest

    # If an older (different) version is installed, remove its chunks first
    if installed_version is not None:
        await uninstall_pack(
            manifest.name,
            settings,
            registry=registry,
            collection=collection,
        )

    # Install the new version (duplicate check inside will pass since we
    # just uninstalled or the pack was never installed)
    return await install_pack(
        pack_path,
        settings,
        registry=registry,
        collection=collection,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _tag_chunks_with_pack(
    collection: Collection,
    chunks: list[DocumentChunk],
    pack_name: str,
) -> None:
    """Update chunk metadata in ChromaDB to include ``pack_name``."""
    if not chunks:
        return

    ids = [str(chunk.id) for chunk in chunks]
    # Fetch existing metadata and add pack_name
    existing = collection.get(ids=ids, include=["metadatas"])
    found_ids = existing.get("ids", ids)
    metadatas = existing.get("metadatas") or []
    updated_metadatas = []
    for meta in metadatas:
        meta = dict(meta) if meta else {}
        meta["pack_name"] = pack_name
        updated_metadatas.append(meta)

    if updated_metadatas:
        # Use found_ids (aligned with metadatas) to avoid length mismatch
        update_ids = found_ids[: len(updated_metadatas)] if found_ids else ids[: len(updated_metadatas)]
        collection.update(ids=update_ids, metadatas=updated_metadatas)


def _delete_pack_chunks(collection: Collection, pack_name: str) -> None:
    """Delete all chunks from the collection that belong to *pack_name*."""
    collection.delete(where={"pack_name": pack_name})


def _remove_pack_files(packs_dir: Path, pack_name: str) -> None:
    """Remove extracted pack directory and/or archive from *packs_dir*.

    Silently skips anything that does not exist so uninstalling an
    already-cleaned pack is safe.
    """
    # Remove extracted directory (e.g. packs/<pack_name>/)
    pack_dir = packs_dir / pack_name
    if pack_dir.is_dir():
        shutil.rmtree(pack_dir)

    # Remove any matching .tar.gz archives (exact name or versioned: name-*.tar.gz)
    if packs_dir.is_dir():
        for archive in packs_dir.glob(f"{pack_name}*.tar.gz"):
            # Only match exact name or name-<version>, not name-sharing prefixes
            stem = archive.name.removesuffix(".tar.gz")
            if stem == pack_name or stem.startswith(f"{pack_name}-"):
                archive.unlink(missing_ok=True)
