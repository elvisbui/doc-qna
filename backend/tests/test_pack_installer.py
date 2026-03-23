"""Tests for the knowledge pack installer."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.packs.builder import build_pack
from app.packs.installer import (
    _remove_pack_files,
    install_pack,
    uninstall_pack,
)
from app.packs.models import PackManifest
from app.packs.registry import PackRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def settings(tmp_path: Path) -> MagicMock:
    """Minimal mock settings."""
    s = MagicMock()
    s.PACKS_DIR = str(tmp_path / "packs")
    s.CHUNKING_STRATEGY = "fixed"
    return s


@pytest.fixture()
def sample_docs(tmp_path: Path) -> list[Path]:
    """Create sample document files."""
    docs_dir = tmp_path / "source_docs"
    docs_dir.mkdir()

    doc1 = docs_dir / "intro.md"
    doc1.write_text("# Introduction\nHello world.", encoding="utf-8")

    doc2 = docs_dir / "guide.txt"
    doc2.write_text("Step 1: Install\nStep 2: Run", encoding="utf-8")

    return [doc1, doc2]


@pytest.fixture()
def built_pack(tmp_path: Path, sample_docs: list[Path]) -> Path:
    """Build a valid pack archive."""
    return build_pack(
        name="test-pack",
        version="0.1.0",
        description="A test pack",
        doc_paths=sample_docs,
        output_dir=tmp_path / "output",
        author="tester",
        license="MIT",
    )


@pytest.fixture()
def registry(tmp_path: Path) -> PackRegistry:
    """Create a fresh registry."""
    packs_dir = tmp_path / "packs"
    packs_dir.mkdir(parents=True, exist_ok=True)
    return PackRegistry(packs_dir)


@pytest.fixture()
def mock_collection() -> MagicMock:
    """Mock ChromaDB collection."""
    collection = MagicMock()
    collection.get.return_value = {"metadatas": [{"document_id": "abc", "chunk_index": 0}]}
    collection.delete.return_value = None
    collection.update.return_value = None
    return collection


# ---------------------------------------------------------------------------
# install_pack tests
# ---------------------------------------------------------------------------


class TestInstallPack:
    @pytest.mark.asyncio
    async def test_install_valid_pack(
        self,
        built_pack: Path,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Installing a valid pack returns its manifest and marks it installed."""
        fake_chunk = MagicMock()
        fake_chunk.id = "chunk-1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ) as mock_ingest:
            manifest = await install_pack(
                built_pack,
                settings,
                registry=registry,
                collection=mock_collection,
            )

        assert isinstance(manifest, PackManifest)
        assert manifest.name == "test-pack"
        assert manifest.version == "0.1.0"
        assert manifest.doc_count == 2

        # ingest_document should have been called once per document
        assert mock_ingest.call_count == 2

        # pack_name metadata should be tagged
        mock_collection.update.assert_called()

        # Registry should reflect installed state
        registry.get_index()
        assert "test-pack" in registry._installed

    @pytest.mark.asyncio
    async def test_install_adds_pack_name_metadata(
        self,
        built_pack: Path,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Chunk metadata is updated with pack_name after ingestion."""
        fake_chunk = MagicMock()
        fake_chunk.id = "chunk-42"

        mock_collection.get.return_value = {
            "metadatas": [{"document_id": "d1", "chunk_index": 0}],
        }

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            await install_pack(
                built_pack,
                settings,
                registry=registry,
                collection=mock_collection,
            )

        # Verify that update was called with pack_name in metadata
        for call in mock_collection.update.call_args_list:
            metadatas = call[1].get("metadatas") or call[0][1] if len(call[0]) > 1 else call[1].get("metadatas")
            if metadatas:
                for meta in metadatas:
                    assert meta.get("pack_name") == "test-pack"

    @pytest.mark.asyncio
    async def test_install_invalid_pack_raises(
        self,
        tmp_path: Path,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Installing a pack that fails validation raises ValueError."""
        bad_pack = tmp_path / "bad.tar.gz"
        bad_pack.write_text("not a real archive")

        with pytest.raises(ValueError, match="Invalid pack"):
            await install_pack(
                bad_pack,
                settings,
                registry=registry,
                collection=mock_collection,
            )

    @pytest.mark.asyncio
    async def test_install_missing_pack_raises(
        self,
        tmp_path: Path,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Installing a non-existent file raises ValueError."""
        with pytest.raises(ValueError, match="Invalid pack"):
            await install_pack(
                tmp_path / "nonexistent.tar.gz",
                settings,
                registry=registry,
                collection=mock_collection,
            )


# ---------------------------------------------------------------------------
# uninstall_pack tests
# ---------------------------------------------------------------------------


class TestUninstallPack:
    @pytest.mark.asyncio
    async def test_uninstall_removes_chunks(
        self,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Uninstalling deletes chunks filtered by pack_name."""
        registry.mark_installed("my-pack")

        await uninstall_pack(
            "my-pack",
            settings,
            registry=registry,
            collection=mock_collection,
        )

        mock_collection.delete.assert_called_once_with(
            where={"pack_name": "my-pack"},
        )

    @pytest.mark.asyncio
    async def test_uninstall_marks_registry(
        self,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Uninstalling marks the pack as uninstalled in the registry."""
        registry.mark_installed("my-pack")
        assert "my-pack" in registry._installed

        await uninstall_pack(
            "my-pack",
            settings,
            registry=registry,
            collection=mock_collection,
        )

        assert "my-pack" not in registry._installed

    @pytest.mark.asyncio
    async def test_uninstall_nonexistent_pack(
        self,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Uninstalling a pack that was never installed still succeeds."""
        await uninstall_pack(
            "never-installed",
            settings,
            registry=registry,
            collection=mock_collection,
        )

        # Should still call delete (ChromaDB handles missing gracefully)
        mock_collection.delete.assert_called_once()
        assert "never-installed" not in registry._installed

    @pytest.mark.asyncio
    async def test_uninstall_removes_extracted_directory(
        self,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Uninstalling removes the extracted pack directory from PACKS_DIR."""
        packs_dir = Path(settings.PACKS_DIR)
        packs_dir.mkdir(parents=True, exist_ok=True)

        # Simulate an extracted pack directory
        pack_dir = packs_dir / "my-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text('{"name": "my-pack"}')
        (pack_dir / "documents").mkdir()
        (pack_dir / "documents" / "doc.txt").write_text("hello")

        registry.mark_installed("my-pack")

        await uninstall_pack(
            "my-pack",
            settings,
            registry=registry,
            collection=mock_collection,
            delete_files=True,
        )

        assert not pack_dir.exists()

    @pytest.mark.asyncio
    async def test_uninstall_removes_archive_file(
        self,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Uninstalling removes .tar.gz archives matching the pack name."""
        packs_dir = Path(settings.PACKS_DIR)
        packs_dir.mkdir(parents=True, exist_ok=True)

        # Simulate archive files in packs dir
        archive = packs_dir / "my-pack-1.0.0.tar.gz"
        archive.write_bytes(b"fake archive")

        registry.mark_installed("my-pack")

        await uninstall_pack(
            "my-pack",
            settings,
            registry=registry,
            collection=mock_collection,
            delete_files=True,
        )

        assert not archive.exists()

    @pytest.mark.asyncio
    async def test_uninstall_removes_both_dir_and_archive(
        self,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Uninstalling removes both the directory and archive if both exist."""
        packs_dir = Path(settings.PACKS_DIR)
        packs_dir.mkdir(parents=True, exist_ok=True)

        pack_dir = packs_dir / "my-pack"
        pack_dir.mkdir()
        (pack_dir / "manifest.json").write_text("{}")

        archive = packs_dir / "my-pack-0.5.0.tar.gz"
        archive.write_bytes(b"fake")

        registry.mark_installed("my-pack")

        await uninstall_pack(
            "my-pack",
            settings,
            registry=registry,
            collection=mock_collection,
            delete_files=True,
        )

        assert not pack_dir.exists()
        assert not archive.exists()
        assert "my-pack" not in registry._installed

    @pytest.mark.asyncio
    async def test_uninstall_no_files_is_safe(
        self,
        settings: MagicMock,
        registry: PackRegistry,
        mock_collection: MagicMock,
    ) -> None:
        """Uninstalling when no pack files exist does not raise."""
        # packs_dir may not even exist yet
        await uninstall_pack(
            "ghost-pack",
            settings,
            registry=registry,
            collection=mock_collection,
        )

        # Should complete without error
        mock_collection.delete.assert_called_once()


# ---------------------------------------------------------------------------
# _remove_pack_files unit tests
# ---------------------------------------------------------------------------


class TestRemovePackFiles:
    def test_removes_directory(self, tmp_path: Path) -> None:
        pack_dir = tmp_path / "my-pack"
        pack_dir.mkdir()
        (pack_dir / "file.txt").write_text("data")

        _remove_pack_files(tmp_path, "my-pack")
        assert not pack_dir.exists()

    def test_removes_archive(self, tmp_path: Path) -> None:
        archive = tmp_path / "my-pack-1.0.0.tar.gz"
        archive.write_bytes(b"fake")

        _remove_pack_files(tmp_path, "my-pack")
        assert not archive.exists()

    def test_removes_multiple_archives(self, tmp_path: Path) -> None:
        a1 = tmp_path / "my-pack-1.0.0.tar.gz"
        a2 = tmp_path / "my-pack-2.0.0.tar.gz"
        a1.write_bytes(b"v1")
        a2.write_bytes(b"v2")

        _remove_pack_files(tmp_path, "my-pack")
        assert not a1.exists()
        assert not a2.exists()

    def test_does_not_remove_unrelated_files(self, tmp_path: Path) -> None:
        other = tmp_path / "other-pack-1.0.0.tar.gz"
        other.write_bytes(b"keep me")

        _remove_pack_files(tmp_path, "my-pack")
        assert other.exists()

    def test_nonexistent_dir_is_safe(self, tmp_path: Path) -> None:
        """No error when packs_dir does not exist."""
        _remove_pack_files(tmp_path / "nonexistent", "my-pack")

    def test_empty_dir_is_safe(self, tmp_path: Path) -> None:
        """No error when packs_dir is empty."""
        _remove_pack_files(tmp_path, "my-pack")
