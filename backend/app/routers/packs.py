"""Packs router -- GET /api/packs, POST /api/packs/{id}/install."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, status

from app.config import get_settings
from app.packs.installer import install_pack as do_install
from app.packs.installer import uninstall_pack as do_uninstall
from app.packs.registry import PackRegistry
from app.schemas.packs import PackDetail, PackListResponse
from app.services.retrieval import invalidate_bm25_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/packs", tags=["packs"])


def _find_pack(index: list[dict], pack_id: str) -> dict | None:
    """Find a pack entry by name in the registry index."""
    for entry in index:
        if entry["name"] == pack_id:
            return entry
    return None


def _get_registry(request: Request) -> PackRegistry:
    """Return a PackRegistry, creating one if not yet on app.state."""
    if hasattr(request.app.state, "pack_registry"):
        return request.app.state.pack_registry
    settings = get_settings()
    registry = PackRegistry(settings.PACKS_DIR)
    request.app.state.pack_registry = registry
    return registry


@router.get(
    "",
    response_model=PackListResponse,
    summary="List available knowledge packs",
)
async def list_packs(request: Request) -> PackListResponse:
    """Return all discovered knowledge packs with their install status."""
    registry = _get_registry(request)
    registry.scan_local()
    index = registry.get_index()
    packs = [PackDetail(**entry) for entry in index]
    return PackListResponse(packs=packs)


@router.get(
    "/{pack_id}/suggested-queries",
    summary="Get suggested queries for a pack",
)
async def get_suggested_queries(pack_id: str, request: Request) -> dict:
    """Return suggested starter queries for a knowledge pack."""
    registry = _get_registry(request)
    entry = _find_pack(registry.get_index(), pack_id)
    if entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pack '{pack_id}' not found",
        )
    return {"pack_id": pack_id, "suggested_queries": entry.get("suggested_queries", [])}


@router.post(
    "/{pack_id}/install",
    response_model=PackDetail,
    summary="Install a knowledge pack",
)
async def install_pack_endpoint(pack_id: str, request: Request) -> PackDetail:
    """Install a knowledge pack by its name/id."""
    registry = _get_registry(request)

    # Ensure the pack exists in the registry
    pack_entry = _find_pack(registry.get_index(), pack_id)
    if pack_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pack '{pack_id}' not found",
        )

    if pack_entry["installed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pack '{pack_id}' is already installed",
        )

    # Find the pack path and run the installer
    settings = get_settings()
    packs_dir = Path(settings.PACKS_DIR)

    # Look for a .tar.gz archive or directory matching pack_id
    pack_path = None
    for candidate in [
        packs_dir / f"{pack_id}.tar.gz",
        packs_dir / pack_id,
    ]:
        if candidate.exists():
            pack_path = candidate
            break

    # Also check versioned archives (e.g., pack_id-1.0.0.tar.gz)
    if pack_path is None:
        for archive in sorted(packs_dir.glob(f"{pack_id}-*.tar.gz"), reverse=True):
            stem = archive.name.removesuffix(".tar.gz")
            if stem.startswith(f"{pack_id}-"):
                pack_path = archive
                break  # Take the latest (sorted reverse)

    if pack_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pack archive for '{pack_id}' not found on disk",
        )

    try:
        manifest = await do_install(
            pack_path=pack_path,
            settings=settings,
            registry=registry,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from None

    invalidate_bm25_cache()

    # Fetch suggested queries for the installed pack
    installed_entry = _find_pack(registry.get_index(), pack_id)
    sq: list[str] = installed_entry.get("suggested_queries", []) if installed_entry else []

    return PackDetail(
        name=manifest.name,
        version=manifest.version,
        description=manifest.description,
        doc_count=manifest.doc_count,
        installed=True,
        installed_version=manifest.version,
        suggested_queries=sq,
    )


@router.post(
    "/{pack_id}/uninstall",
    summary="Uninstall a knowledge pack",
)
async def uninstall_pack_endpoint(pack_id: str, request: Request) -> dict:
    """Uninstall a knowledge pack by removing its chunks and marking it uninstalled."""
    registry = _get_registry(request)

    pack_entry = _find_pack(registry.get_index(), pack_id)
    if pack_entry is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pack '{pack_id}' not found",
        )

    if not pack_entry["installed"]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Pack '{pack_id}' is not installed",
        )

    settings = get_settings()

    try:
        await do_uninstall(
            pack_name=pack_id,
            settings=settings,
            registry=registry,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from None

    invalidate_bm25_cache()

    return {"name": pack_id, "uninstalled": True}
