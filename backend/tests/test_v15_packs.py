"""v1.5 comprehensive tests for packs subsystem.

Covers gaps NOT already tested in:
- test_packs.py (build/read/extract/validate basics)
- test_pack_registry.py (scan, get_index, mark_installed/uninstalled basics)
- test_pack_installer.py (install, uninstall, _remove_pack_files basics)
- test_pack_versioning.py (version tracking, duplicate prevention, upgrade)
- test_cli_pack.py (list/install/remove CLI basics)

Focus areas:
1. Pack format validation — Pydantic schema edge cases, manifest field
   constraints, document structure inside archive
2. Install/uninstall lifecycle — full round-trips, re-install after uninstall,
   lifecycle state consistency
3. Registry parsing — corrupted state recovery, many-pack index, re-scan
   after external mutation, persistence edge cases
4. CLI pack commands — additional smoke tests (help text, edge cases)
5. Pack versioning — downgrade, version string edge cases, upgrade lifecycle
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.packs.builder import build_pack
from app.packs.installer import install_pack, uninstall_pack, upgrade_pack
from app.packs.models import PackManifest, SuggestedQueries
from app.packs.reader import validate_pack
from app.packs.registry import PackRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pack_dir(
    base: Path,
    name: str = "test-pack",
    version: str = "1.0.0",
    doc_names: list[str] | None = None,
    extra_manifest_fields: dict | None = None,
) -> Path:
    """Create a minimal pack directory with manifest and documents."""
    if doc_names is None:
        doc_names = ["doc1.md"]

    pack_dir = base / name
    docs_dir = pack_dir / "documents"
    docs_dir.mkdir(parents=True, exist_ok=True)

    for doc_name in doc_names:
        (docs_dir / doc_name).write_text(f"# {doc_name}\nContent.", encoding="utf-8")

    manifest: dict = {
        "name": name,
        "version": version,
        "description": f"Pack {name}",
        "author": "test",
        "license": "MIT",
        "documents": [f"documents/{d}" for d in doc_names],
        "doc_count": len(doc_names),
    }
    if extra_manifest_fields:
        manifest.update(extra_manifest_fields)

    (pack_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return pack_dir


def _make_pack_archive(
    base: Path,
    name: str = "test-pack",
    version: str = "1.0.0",
    doc_contents: dict[str, str] | None = None,
) -> Path:
    """Build a .tar.gz archive and return its path."""
    docs_dir = base / f"_src_{name}_{version}"
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
        description=f"Pack {name} v{version}",
        doc_paths=doc_paths,
        output_dir=base / f"_out_{name}_{version}",
        author="tester",
        license="MIT",
    )


def _mock_settings(tmp_path: Path) -> MagicMock:
    s = MagicMock()
    s.PACKS_DIR = str(tmp_path / "packs")
    s.CHUNKING_STRATEGY = "fixed"
    return s


def _mock_collection() -> MagicMock:
    col = MagicMock()
    col.get.return_value = {"metadatas": [{"document_id": "d1", "chunk_index": 0}]}
    col.delete.return_value = None
    col.update.return_value = None
    return col


# ===================================================================
# 1. Pack format validation — edge cases
# ===================================================================


class TestManifestSchemaEdgeCases:
    """Pydantic model validation and manifest field constraints."""

    def test_manifest_requires_name(self) -> None:
        """PackManifest should not accept missing name."""
        with pytest.raises(Exception):
            PackManifest(version="1.0.0")  # type: ignore[call-arg]

    def test_manifest_requires_version(self) -> None:
        """PackManifest should not accept missing version."""
        with pytest.raises(Exception):
            PackManifest(name="pack")  # type: ignore[call-arg]

    def test_manifest_defaults_optional_fields(self) -> None:
        """Optional fields should have sensible defaults."""
        m = PackManifest(name="x", version="0.1.0")
        assert m.description == ""
        assert m.author == ""
        assert m.license == ""
        assert m.documents == []
        assert m.doc_count == 0
        assert m.created_at is not None

    def test_manifest_round_trip_json(self) -> None:
        """Serialize to JSON and back yields the same data."""
        m = PackManifest(
            name="rt",
            version="2.0.0",
            description="round-trip",
            documents=["documents/a.md"],
            doc_count=1,
        )
        raw = m.model_dump_json()
        m2 = PackManifest.model_validate_json(raw)
        assert m2.name == m.name
        assert m2.version == m.version
        assert m2.documents == m.documents

    def test_manifest_extra_fields_ignored(self) -> None:
        """Extra fields in JSON should not cause a parse error."""
        data = {
            "name": "extra-pack",
            "version": "1.0.0",
            "description": "has extras",
            "extra_field": "should not crash",
            "documents": [],
            "doc_count": 0,
        }
        m = PackManifest(**data)
        assert m.name == "extra-pack"

    def test_suggested_queries_model(self) -> None:
        """SuggestedQueries model basic behavior."""
        sq = SuggestedQueries(queries=["q1", "q2"])
        assert len(sq.queries) == 2
        sq_empty = SuggestedQueries()
        assert sq_empty.queries == []


class TestPackArchiveStructure:
    """Validate the internal structure of pack archives."""

    def test_archive_has_pack_name_prefix(self, tmp_path: Path) -> None:
        """All archive entries should be under <pack-name>/ prefix."""
        archive = _make_pack_archive(tmp_path, name="prefixed")
        with tarfile.open(archive, "r:gz") as tar:
            for member in tar.getmembers():
                assert member.name.startswith("prefixed"), f"Member {member.name} not under prefixed/"

    def test_archive_manifest_is_valid_json(self, tmp_path: Path) -> None:
        """manifest.json inside the archive should parse without error."""
        archive = _make_pack_archive(tmp_path, name="json-check")
        with tarfile.open(archive, "r:gz") as tar:
            f = tar.extractfile("json-check/manifest.json")
            assert f is not None
            data = json.loads(f.read())
            assert data["name"] == "json-check"

    def test_validate_detects_empty_version(self, tmp_path: Path) -> None:
        """validate_pack should report an error when version is empty."""
        pack_dir = tmp_path / "staging" / "no-ver"
        docs_dir = pack_dir / "documents"
        docs_dir.mkdir(parents=True)
        (docs_dir / "doc.txt").write_text("content")
        manifest = {
            "name": "no-ver",
            "version": "",
            "documents": ["documents/doc.txt"],
            "doc_count": 1,
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))
        archive = tmp_path / "no-ver.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(pack_dir, arcname="no-ver")
        errors = validate_pack(archive)
        assert any("version" in e.lower() for e in errors)

    def test_validate_pack_with_multiple_documents(self, tmp_path: Path) -> None:
        """A pack with multiple documents should validate cleanly."""
        archive = _make_pack_archive(
            tmp_path,
            name="multi-doc",
            doc_contents={"a.md": "A", "b.md": "B", "c.md": "C"},
        )
        errors = validate_pack(archive)
        assert errors == []

    def test_build_pack_invalid_version_empty(self, tmp_path: Path) -> None:
        """build_pack should work with any version string (no strict semver)."""
        doc = tmp_path / "doc.md"
        doc.write_text("hi")
        # Empty version is technically allowed by build_pack; validation catches it
        pack = build_pack(
            name="ev",
            version="",
            description="empty version",
            doc_paths=[doc],
            output_dir=tmp_path / "out",
        )
        # The pack builds, but validate_pack should catch the empty version
        errors = validate_pack(pack)
        assert any("version" in e.lower() for e in errors)


# ===================================================================
# 2. Install/uninstall lifecycle — round-trips
# ===================================================================


class TestInstallUninstallRoundTrip:
    """Full install -> verify -> uninstall -> verify cycles."""

    @pytest.fixture()
    def env(self, tmp_path: Path):
        """Common test environment."""

        class Env:
            pass

        e = Env()
        e.settings = _mock_settings(tmp_path)
        packs_dir = Path(e.settings.PACKS_DIR)
        packs_dir.mkdir(parents=True, exist_ok=True)
        e.registry = PackRegistry(packs_dir)
        e.collection = _mock_collection()
        e.tmp_path = tmp_path
        return e

    @pytest.mark.asyncio
    async def test_install_then_uninstall_clears_state(self, env) -> None:
        """After install + uninstall, the registry should show pack as not installed."""
        pack = _make_pack_archive(env.tmp_path, name="lifecycle-pack", version="1.0.0")
        fake_chunk = MagicMock()
        fake_chunk.id = "c1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            manifest = await install_pack(
                pack,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )

        assert manifest.name == "lifecycle-pack"
        assert "lifecycle-pack" in env.registry._installed
        assert env.registry.get_installed_version("lifecycle-pack") == "1.0.0"

        await uninstall_pack(
            "lifecycle-pack",
            env.settings,
            registry=env.registry,
            collection=env.collection,
        )

        assert "lifecycle-pack" not in env.registry._installed
        assert env.registry.get_installed_version("lifecycle-pack") is None
        env.collection.delete.assert_called_with(where={"pack_name": "lifecycle-pack"})

    @pytest.mark.asyncio
    async def test_reinstall_after_uninstall(self, env) -> None:
        """A pack can be re-installed after being uninstalled."""
        pack = _make_pack_archive(env.tmp_path, name="reins-pack", version="1.0.0")
        fake_chunk = MagicMock()
        fake_chunk.id = "c1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ) as mock_ingest:
            await install_pack(
                pack,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )
            first_count = mock_ingest.call_count

            await uninstall_pack(
                "reins-pack",
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )

            # Re-install should trigger ingestion again
            await install_pack(
                pack,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )
            assert mock_ingest.call_count > first_count

        assert "reins-pack" in env.registry._installed

    @pytest.mark.asyncio
    async def test_install_multiple_packs(self, env) -> None:
        """Multiple different packs can be installed concurrently."""
        pack_a = _make_pack_archive(env.tmp_path, name="pack-a", version="1.0.0")
        pack_b = _make_pack_archive(env.tmp_path, name="pack-b", version="2.0.0")
        fake_chunk = MagicMock()
        fake_chunk.id = "c1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            await install_pack(
                pack_a,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )
            await install_pack(
                pack_b,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )

        assert "pack-a" in env.registry._installed
        assert "pack-b" in env.registry._installed
        assert env.registry.get_installed_version("pack-a") == "1.0.0"
        assert env.registry.get_installed_version("pack-b") == "2.0.0"

    @pytest.mark.asyncio
    async def test_uninstall_one_does_not_affect_other(self, env) -> None:
        """Uninstalling one pack leaves other installed packs untouched."""
        pack_a = _make_pack_archive(env.tmp_path, name="keep-me", version="1.0.0")
        pack_b = _make_pack_archive(env.tmp_path, name="remove-me", version="1.0.0")
        fake_chunk = MagicMock()
        fake_chunk.id = "c1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            await install_pack(
                pack_a,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )
            await install_pack(
                pack_b,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )

        await uninstall_pack(
            "remove-me",
            env.settings,
            registry=env.registry,
            collection=env.collection,
        )

        assert "keep-me" in env.registry._installed
        assert "remove-me" not in env.registry._installed


# ===================================================================
# 3. Registry parsing — edge cases
# ===================================================================


class TestRegistryEdgeCases:
    def test_corrupted_registry_json_recovers(self, tmp_path: Path) -> None:
        """A corrupted registry.json should be silently reset."""
        state_file = tmp_path / "registry.json"
        state_file.write_text("{{{invalid json!!!", encoding="utf-8")

        reg = PackRegistry(tmp_path)
        assert reg._installed == set()
        assert reg._versions == {}

    def test_empty_registry_json_recovers(self, tmp_path: Path) -> None:
        """An empty registry.json should not crash."""
        state_file = tmp_path / "registry.json"
        state_file.write_text("", encoding="utf-8")

        reg = PackRegistry(tmp_path)
        assert reg._installed == set()

    def test_registry_json_missing_keys(self, tmp_path: Path) -> None:
        """registry.json without expected keys should fall back to defaults."""
        state_file = tmp_path / "registry.json"
        state_file.write_text("{}", encoding="utf-8")

        reg = PackRegistry(tmp_path)
        assert reg._installed == set()
        assert reg._versions == {}

    def test_scan_many_packs(self, tmp_path: Path) -> None:
        """Registry handles many packs without issue."""
        for i in range(20):
            _make_pack_dir(tmp_path, name=f"pack-{i:03d}", version=f"{i}.0.0")

        reg = PackRegistry(tmp_path)
        manifests = reg.scan_local()
        assert len(manifests) == 20

    def test_rescan_after_external_add(self, tmp_path: Path) -> None:
        """Re-scanning discovers packs added after initial scan."""
        reg = PackRegistry(tmp_path)
        assert reg.scan_local() == []

        _make_pack_dir(tmp_path, name="late-arrival")
        manifests = reg.scan_local()
        assert len(manifests) == 1
        assert manifests[0].name == "late-arrival"

    def test_rescan_after_external_removal(self, tmp_path: Path) -> None:
        """Re-scanning reflects packs removed from disk."""
        _make_pack_dir(tmp_path, name="ephemeral")
        reg = PackRegistry(tmp_path)
        assert len(reg.scan_local()) == 1

        import shutil

        shutil.rmtree(tmp_path / "ephemeral")

        # Rescan only picks up existing packs (registry.json stays)
        manifests = reg.scan_local()
        pack_names = {m.name for m in manifests}
        assert "ephemeral" not in pack_names

    def test_get_index_installed_flag_consistency(self, tmp_path: Path) -> None:
        """get_index installed flag should be consistent with mark_installed."""
        _make_pack_dir(tmp_path, name="flag-pack")
        reg = PackRegistry(tmp_path)
        reg.scan_local()

        index = reg.get_index()
        assert index[0]["installed"] is False

        reg.mark_installed("flag-pack", version="1.0.0")
        index = reg.get_index()
        assert index[0]["installed"] is True
        assert index[0]["installed_version"] == "1.0.0"

    def test_registry_persists_multiple_packs_with_versions(self, tmp_path: Path) -> None:
        """Version info for multiple packs survives reload."""
        reg = PackRegistry(tmp_path)
        reg.mark_installed("alpha", version="1.0.0")
        reg.mark_installed("beta", version="2.5.0")
        reg.mark_installed("gamma", version="0.1.0")

        reg2 = PackRegistry(tmp_path)
        assert reg2.get_installed_version("alpha") == "1.0.0"
        assert reg2.get_installed_version("beta") == "2.5.0"
        assert reg2.get_installed_version("gamma") == "0.1.0"

    def test_scan_skips_registry_json(self, tmp_path: Path) -> None:
        """registry.json itself should not be treated as a pack."""
        _make_pack_dir(tmp_path, name="real-pack")
        reg = PackRegistry(tmp_path)
        reg.mark_installed("real-pack")  # creates registry.json

        manifests = reg.scan_local()
        assert len(manifests) == 1
        assert manifests[0].name == "real-pack"

    def test_get_index_includes_description(self, tmp_path: Path) -> None:
        """Index entries should include the description field."""
        _make_pack_dir(tmp_path, name="desc-pack")
        reg = PackRegistry(tmp_path)
        reg.scan_local()
        index = reg.get_index()
        assert "description" in index[0]
        assert "desc-pack" in index[0]["description"] or index[0]["description"]


# ===================================================================
# 4. CLI pack commands — additional smoke tests
# ===================================================================


class TestCLIPackSmoke:
    """Smoke tests for CLI pack subcommands using the Typer test runner."""

    @pytest.fixture(autouse=True)
    def _setup_runner(self):
        from typer.testing import CliRunner

        from app.cli import app

        self.runner = CliRunner()
        self.app = app

    def test_pack_list_help(self) -> None:
        """``pack list --help`` should exit 0 and show usage info."""
        result = self.runner.invoke(self.app, ["pack", "list", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output.lower() or "show" in result.output.lower()

    def test_pack_install_help(self) -> None:
        """``pack install --help`` should exit 0."""
        result = self.runner.invoke(self.app, ["pack", "install", "--help"])
        assert result.exit_code == 0

    def test_pack_remove_help(self) -> None:
        """``pack remove --help`` should exit 0."""
        result = self.runner.invoke(self.app, ["pack", "remove", "--help"])
        assert result.exit_code == 0

    def test_pack_list_with_installed_marker(self) -> None:
        """``pack list`` output should show installed status."""
        fake_index = [
            {
                "name": "installed-pack",
                "version": "1.0.0",
                "description": "Already installed",
                "doc_count": 3,
                "installed": True,
            },
        ]
        with patch("app.packs.registry.PackRegistry") as MockReg:
            inst = MockReg.return_value
            inst.scan_local.return_value = []
            inst.get_index.return_value = fake_index
            result = self.runner.invoke(self.app, ["pack", "list"])

        assert result.exit_code == 0
        assert "installed-pack" in result.output

    def test_pack_install_invokes_install_pack(self, tmp_path) -> None:
        """``pack install`` should delegate to install_pack."""
        fake_pack = tmp_path / "cli-test.tar.gz"
        fake_pack.write_bytes(b"fake")
        fake_manifest = MagicMock()
        fake_manifest.name = "cli-test"
        fake_manifest.version = "1.0.0"

        with patch(
            "app.packs.installer.install_pack",
            new_callable=AsyncMock,
            return_value=fake_manifest,
        ) as mock_install:
            result = self.runner.invoke(self.app, ["pack", "install", str(fake_pack)])

        assert result.exit_code == 0
        mock_install.assert_called_once()

    def test_pack_remove_invokes_uninstall_pack(self) -> None:
        """``pack remove`` should delegate to uninstall_pack."""
        with patch(
            "app.packs.installer.uninstall_pack",
            new_callable=AsyncMock,
        ) as mock_uninstall:
            result = self.runner.invoke(self.app, ["pack", "remove", "some-pack"])

        assert result.exit_code == 0
        mock_uninstall.assert_called_once()


# ===================================================================
# 5. Pack versioning — additional edge cases
# ===================================================================


class TestVersioningEdgeCases:
    @pytest.fixture()
    def env(self, tmp_path: Path):
        class Env:
            pass

        e = Env()
        e.settings = _mock_settings(tmp_path)
        packs_dir = Path(e.settings.PACKS_DIR)
        packs_dir.mkdir(parents=True, exist_ok=True)
        e.registry = PackRegistry(packs_dir)
        e.collection = _mock_collection()
        e.tmp_path = tmp_path
        return e

    @pytest.mark.asyncio
    async def test_downgrade_replaces_version(self, env) -> None:
        """upgrade_pack with a lower version should still replace the old one."""
        v2 = _make_pack_archive(env.tmp_path, name="dg-pack", version="2.0.0")
        v1 = _make_pack_archive(env.tmp_path, name="dg-pack", version="1.0.0")
        fake_chunk = MagicMock()
        fake_chunk.id = "c1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            await install_pack(
                v2,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )
            assert env.registry.get_installed_version("dg-pack") == "2.0.0"

            m = await upgrade_pack(
                v1,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )

        assert m.version == "1.0.0"
        assert env.registry.get_installed_version("dg-pack") == "1.0.0"
        # Old chunks should have been deleted before re-install
        env.collection.delete.assert_called_with(where={"pack_name": "dg-pack"})

    @pytest.mark.asyncio
    async def test_upgrade_preserves_other_packs(self, env) -> None:
        """Upgrading one pack should not affect another installed pack."""
        pack_a = _make_pack_archive(env.tmp_path, name="stable", version="1.0.0")
        pack_b_v1 = _make_pack_archive(env.tmp_path, name="changing", version="1.0.0")
        pack_b_v2 = _make_pack_archive(env.tmp_path, name="changing", version="2.0.0")
        fake_chunk = MagicMock()
        fake_chunk.id = "c1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            await install_pack(
                pack_a,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )
            await install_pack(
                pack_b_v1,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )
            await upgrade_pack(
                pack_b_v2,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )

        assert env.registry.get_installed_version("stable") == "1.0.0"
        assert env.registry.get_installed_version("changing") == "2.0.0"

    def test_version_with_prerelease_string(self, tmp_path: Path) -> None:
        """Registry should store arbitrary version strings (e.g. pre-release)."""
        reg = PackRegistry(tmp_path)
        reg.mark_installed("pre-pack", version="1.0.0-beta.3")
        assert reg.get_installed_version("pre-pack") == "1.0.0-beta.3"

        reg2 = PackRegistry(tmp_path)
        assert reg2.get_installed_version("pre-pack") == "1.0.0-beta.3"

    def test_version_with_build_metadata(self, tmp_path: Path) -> None:
        """Version strings with build metadata should be stored faithfully."""
        reg = PackRegistry(tmp_path)
        reg.mark_installed("bm-pack", version="1.0.0+build.42")

        reg2 = PackRegistry(tmp_path)
        assert reg2.get_installed_version("bm-pack") == "1.0.0+build.42"

    @pytest.mark.asyncio
    async def test_upgrade_invalid_pack_raises(self, env) -> None:
        """upgrade_pack with an invalid archive should raise ValueError."""
        bad = env.tmp_path / "bad.tar.gz"
        bad.write_text("not real")

        with pytest.raises(ValueError, match="Invalid pack"):
            await upgrade_pack(
                bad,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )

    @pytest.mark.asyncio
    async def test_install_records_version_in_state_file(self, env) -> None:
        """After install, the version should be in registry.json on disk."""
        pack = _make_pack_archive(env.tmp_path, name="disk-ver", version="3.1.0")
        fake_chunk = MagicMock()
        fake_chunk.id = "c1"

        with patch(
            "app.packs.installer.ingest_document",
            new_callable=AsyncMock,
            return_value=[fake_chunk],
        ):
            await install_pack(
                pack,
                env.settings,
                registry=env.registry,
                collection=env.collection,
            )

        state_file = Path(env.settings.PACKS_DIR) / "registry.json"
        assert state_file.is_file()
        data = json.loads(state_file.read_text(encoding="utf-8"))
        assert "disk-ver" in data["installed"]
        assert data["versions"]["disk-ver"] == "3.1.0"
