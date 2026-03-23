"""Tests for pack versioning and upgrade functionality."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.packs.builder import build_pack
from app.packs.installer import install_pack, upgrade_pack
from app.packs.registry import PackRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_pack_dir(
    base: Path,
    name: str = "test-pack",
    version: str = "1.0.0",
    doc_names: list[str] | None = None,
) -> Path:
    """Create a minimal pack directory with manifest and documents."""
    if doc_names is None:
        doc_names = ["doc1.md"]

    pack_dir = base / name
    docs_dir = pack_dir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    for doc_name in doc_names:
        (docs_dir / doc_name).write_text(f"# {doc_name}\nSample content.", encoding="utf-8")

    manifest = {
        "name": name,
        "version": version,
        "description": f"Test pack: {name}",
        "author": "test",
        "license": "MIT",
        "documents": [f"documents/{d}" for d in doc_names],
        "doc_count": len(doc_names),
    }
    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return pack_dir


def _build_pack_archive(
    tmp_path: Path,
    name: str = "test-pack",
    version: str = "1.0.0",
    doc_contents: dict[str, str] | None = None,
) -> Path:
    """Build a .tar.gz pack archive for testing."""
    docs_dir = tmp_path / f"docs_{version}"
    docs_dir.mkdir(parents=True, exist_ok=True)

    if doc_contents is None:
        doc_contents = {"intro.md": f"# Intro v{version}\nContent."}

    doc_paths = []
    for fname, content in doc_contents.items():
        p = docs_dir / fname
        p.write_text(content, encoding="utf-8")
        doc_paths.append(p)

    return build_pack(
        name=name,
        version=version,
        description=f"Test pack v{version}",
        doc_paths=doc_paths,
        output_dir=tmp_path / f"output_{version}",
        author="tester",
        license="MIT",
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def settings(tmp_path: Path) -> MagicMock:
    s = MagicMock()
    s.PACKS_DIR = str(tmp_path / "packs")
    s.CHUNKING_STRATEGY = "fixed"
    return s


@pytest.fixture()
def registry(tmp_path: Path) -> PackRegistry:
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir(parents=True, exist_ok=True)
    return PackRegistry(packs_dir)


@pytest.fixture()
def mock_collection() -> MagicMock:
    collection = MagicMock()
    collection.get.return_value = {"metadatas": [{"document_id": "abc", "chunk_index": 0}]}
    collection.delete.return_value = None
    collection.update.return_value = None
    return collection


# ---------------------------------------------------------------------------
# Tests — Registry version tracking
# ---------------------------------------------------------------------------


class TestRegistryVersionTracking:
    def test_mark_installed_with_version(self, tmp_path: Path) -> None:
        """mark_installed stores the version alongside the pack name."""
        reg = PackRegistry(tmp_path)
        reg.mark_installed("my-pack", version="1.0.0")
        assert reg.get_installed_version("my-pack") == "1.0.0"

    def test_mark_installed_updates_version(self, tmp_path: Path) -> None:
        """Calling mark_installed again with a new version updates it."""
        reg = PackRegistry(tmp_path)
        reg.mark_installed("my-pack", version="1.0.0")
        reg.mark_installed("my-pack", version="2.0.0")
        assert reg.get_installed_version("my-pack") == "2.0.0"

    def test_version_persists_to_disk(self, tmp_path: Path) -> None:
        """Version info survives registry reload."""
        reg1 = PackRegistry(tmp_path)
        reg1.mark_installed("my-pack", version="3.0.0")

        reg2 = PackRegistry(tmp_path)
        assert reg2.get_installed_version("my-pack") == "3.0.0"

    def test_get_installed_version_returns_none_if_not_installed(self, tmp_path: Path) -> None:
        reg = PackRegistry(tmp_path)
        assert reg.get_installed_version("nonexistent") is None

    def test_mark_uninstalled_clears_version(self, tmp_path: Path) -> None:
        reg = PackRegistry(tmp_path)
        reg.mark_installed("my-pack", version="1.0.0")
        reg.mark_uninstalled("my-pack")
        assert reg.get_installed_version("my-pack") is None

    def test_get_index_includes_installed_version(self, tmp_path: Path) -> None:
        """get_index should include the installed_version field."""
        _create_pack_dir(tmp_path, name="idx-pack", version="2.0.0")
        reg = PackRegistry(tmp_path)
        reg.scan_local()
        reg.mark_installed("idx-pack", version="2.0.0")

        index = reg.get_index()
        assert len(index) == 1
        assert index[0]["installed_version"] == "2.0.0"

    def test_backward_compat_old_state_format(self, tmp_path: Path) -> None:
        """A registry.json with old list format still loads correctly."""
        state_file = tmp_path / "registry.json"
        state_file.write_text(json.dumps({"installed": ["old-pack"]}), encoding="utf-8")

        reg = PackRegistry(tmp_path)
        assert "old-pack" in reg._installed
        # Old packs get no version
        assert reg.get_installed_version("old-pack") is None


# ---------------------------------------------------------------------------
# Tests — Duplicate chunk prevention
# ---------------------------------------------------------------------------


class TestDuplicatePrevention:
    @pytest.mark.asyncio
    async def test_install_same_version_twice_skips(
        self,
        tmp_path: Path,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Re-installing an already-installed pack at the same version is a no-op."""
        pack_path = _build_pack_archive(tmp_path, name="dup-pack", version="1.0.0")

        fake_chunk = MagicMock()
        fake_chunk.id = "chunk-1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ) as mock_ingest:
            # First install
            await install_pack(
                pack_path,
                settings,
                registry=registry,
                collection=mock_collection,
            )
            first_call_count = mock_ingest.call_count

            # Second install — same version, should skip
            manifest = await install_pack(
                pack_path,
                settings,
                registry=registry,
                collection=mock_collection,
            )

            # ingest_document should NOT have been called again
            assert mock_ingest.call_count == first_call_count

        assert manifest.name == "dup-pack"


# ---------------------------------------------------------------------------
# Tests — upgrade_pack
# ---------------------------------------------------------------------------


class TestUpgradePack:
    @pytest.mark.asyncio
    async def test_upgrade_replaces_old_version(
        self,
        tmp_path: Path,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """upgrade_pack uninstalls old chunks and installs the new version."""
        old_pack = _build_pack_archive(tmp_path, name="up-pack", version="1.0.0")
        new_pack = _build_pack_archive(tmp_path, name="up-pack", version="2.0.0")

        fake_chunk = MagicMock()
        fake_chunk.id = "chunk-1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            # Install v1
            await install_pack(
                old_pack,
                settings,
                registry=registry,
                collection=mock_collection,
            )
            assert registry.get_installed_version("up-pack") == "1.0.0"

            # Upgrade to v2
            manifest = await upgrade_pack(
                new_pack,
                settings,
                registry=registry,
                collection=mock_collection,
            )

        assert manifest.version == "2.0.0"
        assert registry.get_installed_version("up-pack") == "2.0.0"

        # Old chunks should have been deleted
        mock_collection.delete.assert_called_with(where={"pack_name": "up-pack"})

    @pytest.mark.asyncio
    async def test_upgrade_same_version_skips(
        self,
        tmp_path: Path,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Upgrading to the same version already installed is a no-op."""
        pack_path = _build_pack_archive(tmp_path, name="same-pack", version="1.0.0")

        fake_chunk = MagicMock()
        fake_chunk.id = "chunk-1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ) as mock_ingest:
            await install_pack(
                pack_path,
                settings,
                registry=registry,
                collection=mock_collection,
            )
            call_count_after_install = mock_ingest.call_count

            manifest = await upgrade_pack(
                pack_path,
                settings,
                registry=registry,
                collection=mock_collection,
            )

            # Should NOT have re-ingested
            assert mock_ingest.call_count == call_count_after_install

        assert manifest.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_upgrade_not_installed_acts_as_install(
        self,
        tmp_path: Path,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Upgrading a pack that isn't installed yet just installs it."""
        pack_path = _build_pack_archive(tmp_path, name="fresh-pack", version="1.0.0")

        fake_chunk = MagicMock()
        fake_chunk.id = "chunk-1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            manifest = await upgrade_pack(
                pack_path,
                settings,
                registry=registry,
                collection=mock_collection,
            )

        assert manifest.name == "fresh-pack"
        assert registry.get_installed_version("fresh-pack") == "1.0.0"
        # Should NOT have called delete since nothing was installed before
        mock_collection.delete.assert_not_called()
