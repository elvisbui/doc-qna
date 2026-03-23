"""Tests for the PackRegistry class."""

from __future__ import annotations

import json
import tarfile
import tempfile
from pathlib import Path

from app.packs.models import PackManifest
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
    docs_dir.mkdir(parents=True)

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


def _create_pack_archive(
    base: Path,
    name: str = "archive-pack",
    version: str = "1.0.0",
) -> Path:
    """Create a .tar.gz pack archive in *base* and return its path."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pack_dir = _create_pack_dir(tmp_path, name=name, version=version)
        archive_path = base / f"{name}-{version}.tar.gz"
        with tarfile.open(archive_path, "w:gz") as tar:
            tar.add(pack_dir, arcname=name)
    return archive_path


# ---------------------------------------------------------------------------
# Tests — scan_local
# ---------------------------------------------------------------------------


class TestScanLocal:
    def test_scan_discovers_pack_directories(self, tmp_path: Path) -> None:
        _create_pack_dir(tmp_path, name="pack-a")
        _create_pack_dir(tmp_path, name="pack-b", doc_names=["a.md", "b.md"])

        registry = PackRegistry(tmp_path)
        manifests = registry.scan_local()

        assert len(manifests) == 2
        names = {m.name for m in manifests}
        assert names == {"pack-a", "pack-b"}

    def test_scan_discovers_tar_gz_archives(self, tmp_path: Path) -> None:
        _create_pack_archive(tmp_path, name="archived-pack")

        registry = PackRegistry(tmp_path)
        manifests = registry.scan_local()

        assert len(manifests) == 1
        assert manifests[0].name == "archived-pack"

    def test_scan_mixed_dirs_and_archives(self, tmp_path: Path) -> None:
        _create_pack_dir(tmp_path, name="dir-pack")
        _create_pack_archive(tmp_path, name="tar-pack")

        registry = PackRegistry(tmp_path)
        manifests = registry.scan_local()

        assert len(manifests) == 2
        names = {m.name for m in manifests}
        assert names == {"dir-pack", "tar-pack"}

    def test_scan_ignores_dirs_without_manifest(self, tmp_path: Path) -> None:
        (tmp_path / "no-manifest").mkdir()
        _create_pack_dir(tmp_path, name="valid")

        registry = PackRegistry(tmp_path)
        manifests = registry.scan_local()

        assert len(manifests) == 1
        assert manifests[0].name == "valid"

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        registry = PackRegistry(tmp_path)
        manifests = registry.scan_local()
        assert manifests == []

    def test_scan_nonexistent_directory(self, tmp_path: Path) -> None:
        registry = PackRegistry(tmp_path / "does-not-exist")
        manifests = registry.scan_local()
        assert manifests == []

    def test_scan_returns_pack_manifests(self, tmp_path: Path) -> None:
        _create_pack_dir(tmp_path, name="my-pack", version="2.0.0", doc_names=["x.md", "y.md"])

        registry = PackRegistry(tmp_path)
        manifests = registry.scan_local()

        assert len(manifests) == 1
        m = manifests[0]
        assert isinstance(m, PackManifest)
        assert m.name == "my-pack"
        assert m.version == "2.0.0"
        assert m.doc_count == 2


# ---------------------------------------------------------------------------
# Tests — get_index
# ---------------------------------------------------------------------------


class TestGetIndex:
    def test_index_contains_expected_fields(self, tmp_path: Path) -> None:
        _create_pack_dir(tmp_path, name="idx-pack", version="1.2.0", doc_names=["a.md"])

        registry = PackRegistry(tmp_path)
        registry.scan_local()
        index = registry.get_index()

        assert len(index) == 1
        entry = index[0]
        assert entry["name"] == "idx-pack"
        assert entry["version"] == "1.2.0"
        assert entry["doc_count"] == 1
        assert entry["installed"] is False
        assert "description" in entry

    def test_index_reflects_installed_status(self, tmp_path: Path) -> None:
        _create_pack_dir(tmp_path, name="inst-pack")

        registry = PackRegistry(tmp_path)
        registry.scan_local()
        registry.mark_installed("inst-pack")

        index = registry.get_index()
        assert index[0]["installed"] is True

    def test_index_auto_scans_if_needed(self, tmp_path: Path) -> None:
        _create_pack_dir(tmp_path, name="auto-pack")

        registry = PackRegistry(tmp_path)
        # Do not call scan_local explicitly
        index = registry.get_index()

        assert len(index) == 1
        assert index[0]["name"] == "auto-pack"


# ---------------------------------------------------------------------------
# Tests — mark_installed / mark_uninstalled
# ---------------------------------------------------------------------------


class TestInstallState:
    def test_mark_installed(self, tmp_path: Path) -> None:
        registry = PackRegistry(tmp_path)
        registry.mark_installed("pack-x")
        assert "pack-x" in registry._installed

    def test_mark_uninstalled(self, tmp_path: Path) -> None:
        registry = PackRegistry(tmp_path)
        registry.mark_installed("pack-x")
        registry.mark_uninstalled("pack-x")
        assert "pack-x" not in registry._installed

    def test_mark_uninstalled_noop_if_not_installed(self, tmp_path: Path) -> None:
        registry = PackRegistry(tmp_path)
        registry.mark_uninstalled("nonexistent")
        assert "nonexistent" not in registry._installed

    def test_state_persists_to_registry_json(self, tmp_path: Path) -> None:
        registry = PackRegistry(tmp_path)
        registry.mark_installed("alpha")
        registry.mark_installed("beta")

        state_file = tmp_path / "registry.json"
        assert state_file.is_file()

        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert set(data["installed"]) == {"alpha", "beta"}

    def test_state_loads_on_init(self, tmp_path: Path) -> None:
        # Create initial state
        registry1 = PackRegistry(tmp_path)
        registry1.mark_installed("persisted-pack")

        # New instance should load the state
        registry2 = PackRegistry(tmp_path)
        assert "persisted-pack" in registry2._installed

    def test_uninstall_persists(self, tmp_path: Path) -> None:
        registry1 = PackRegistry(tmp_path)
        registry1.mark_installed("temp-pack")
        registry1.mark_uninstalled("temp-pack")

        registry2 = PackRegistry(tmp_path)
        assert "temp-pack" not in registry2._installed


# ---------------------------------------------------------------------------
# Tests — suggested queries
# ---------------------------------------------------------------------------


class TestSuggestedQueries:
    def test_loads_suggested_queries_from_directory(self, tmp_path: Path) -> None:
        pack_dir = _create_pack_dir(tmp_path, name="sq-pack")
        queries = {"queries": ["What is X?", "How does Y work?"]}
        (pack_dir / "suggested_queries.json").write_text(json.dumps(queries), encoding="utf-8")

        registry = PackRegistry(tmp_path)
        registry.scan_local()
        index = registry.get_index()

        assert len(index) == 1
        assert index[0]["suggested_queries"] == ["What is X?", "How does Y work?"]

    def test_empty_list_when_no_suggested_queries_file(self, tmp_path: Path) -> None:
        _create_pack_dir(tmp_path, name="no-sq-pack")

        registry = PackRegistry(tmp_path)
        registry.scan_local()
        index = registry.get_index()

        assert index[0]["suggested_queries"] == []

    def test_suggested_queries_from_archive(self, tmp_path: Path) -> None:
        """Suggested queries are loaded from .tar.gz archives."""
        import tarfile as _tarfile

        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            pack_dir = _create_pack_dir(tmp_p, name="arch-sq")
            queries = {"queries": ["Archive question?"]}
            (pack_dir / "suggested_queries.json").write_text(json.dumps(queries), encoding="utf-8")
            archive_path = tmp_path / "arch-sq-1.0.0.tar.gz"
            with _tarfile.open(archive_path, "w:gz") as tar:
                tar.add(pack_dir, arcname="arch-sq")

        registry = PackRegistry(tmp_path)
        registry.scan_local()
        index = registry.get_index()

        assert len(index) == 1
        assert index[0]["suggested_queries"] == ["Archive question?"]

    def test_malformed_suggested_queries_returns_empty(self, tmp_path: Path) -> None:
        pack_dir = _create_pack_dir(tmp_path, name="bad-sq")
        (pack_dir / "suggested_queries.json").write_text("NOT VALID JSON", encoding="utf-8")

        registry = PackRegistry(tmp_path)
        registry.scan_local()
        index = registry.get_index()

        assert index[0]["suggested_queries"] == []
