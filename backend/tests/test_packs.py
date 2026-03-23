"""Tests for the knowledge pack format."""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

import pytest

from app.packs.builder import build_pack
from app.packs.models import PackManifest
from app.packs.reader import extract_pack, read_manifest, validate_pack

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_docs(tmp_path: Path) -> list[Path]:
    """Create a handful of sample document files."""
    docs_dir = tmp_path / "source_docs"
    docs_dir.mkdir()

    doc1 = docs_dir / "intro.md"
    doc1.write_text("# Introduction\nHello world.", encoding="utf-8")

    doc2 = docs_dir / "guide.txt"
    doc2.write_text("Step 1: Install\nStep 2: Run", encoding="utf-8")

    return [doc1, doc2]


@pytest.fixture()
def built_pack(tmp_path: Path, sample_docs: list[Path]) -> Path:
    """Build a pack and return its archive path."""
    return build_pack(
        name="test-pack",
        version="0.1.0",
        description="A test pack",
        doc_paths=sample_docs,
        output_dir=tmp_path / "output",
        author="tester",
        license="MIT",
        suggested_queries=["What is this?", "How do I use it?"],
    )


# ---------------------------------------------------------------------------
# build_pack tests
# ---------------------------------------------------------------------------


class TestBuildPack:
    def test_creates_tar_gz(self, built_pack: Path) -> None:
        assert built_pack.exists()
        assert built_pack.name == "test-pack-0.1.0.tar.gz"

    def test_archive_contains_manifest(self, built_pack: Path) -> None:
        with tarfile.open(built_pack, "r:gz") as tar:
            names = tar.getnames()
            assert "test-pack/manifest.json" in names

    def test_archive_contains_documents(self, built_pack: Path) -> None:
        with tarfile.open(built_pack, "r:gz") as tar:
            names = tar.getnames()
            assert "test-pack/documents/intro.md" in names
            assert "test-pack/documents/guide.txt" in names

    def test_archive_contains_suggested_queries(self, built_pack: Path) -> None:
        with tarfile.open(built_pack, "r:gz") as tar:
            names = tar.getnames()
            assert "test-pack/suggested_queries.json" in names

            f = tar.extractfile("test-pack/suggested_queries.json")
            assert f is not None
            data = json.loads(f.read())
            assert data["queries"] == ["What is this?", "How do I use it?"]

    def test_manifest_content(self, built_pack: Path) -> None:
        with tarfile.open(built_pack, "r:gz") as tar:
            f = tar.extractfile("test-pack/manifest.json")
            assert f is not None
            data = json.loads(f.read())

        assert data["name"] == "test-pack"
        assert data["version"] == "0.1.0"
        assert data["description"] == "A test pack"
        assert data["author"] == "tester"
        assert data["license"] == "MIT"
        assert data["doc_count"] == 2
        assert "documents/intro.md" in data["documents"]
        assert "documents/guide.txt" in data["documents"]
        assert "created_at" in data

    def test_no_suggested_queries(self, tmp_path: Path, sample_docs: list[Path]) -> None:
        pack = build_pack(
            name="minimal",
            version="1.0.0",
            description="No queries",
            doc_paths=sample_docs,
            output_dir=tmp_path / "out",
        )
        with tarfile.open(pack, "r:gz") as tar:
            names = tar.getnames()
            assert not any("suggested_queries" in n for n in names)

    def test_empty_name_raises(self, tmp_path: Path, sample_docs: list[Path]) -> None:
        with pytest.raises(ValueError, match="name must not be empty"):
            build_pack(
                name="",
                version="1.0.0",
                description="bad",
                doc_paths=sample_docs,
                output_dir=tmp_path,
            )

    def test_no_docs_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="(?i)at least one document"):
            build_pack(
                name="empty",
                version="1.0.0",
                description="bad",
                doc_paths=[],
                output_dir=tmp_path,
            )

    def test_missing_doc_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            build_pack(
                name="bad",
                version="1.0.0",
                description="bad",
                doc_paths=[tmp_path / "nope.txt"],
                output_dir=tmp_path,
            )


# ---------------------------------------------------------------------------
# read_manifest tests
# ---------------------------------------------------------------------------


class TestReadManifest:
    def test_reads_manifest(self, built_pack: Path) -> None:
        manifest = read_manifest(built_pack)
        assert isinstance(manifest, PackManifest)
        assert manifest.name == "test-pack"
        assert manifest.version == "0.1.0"
        assert manifest.doc_count == 2
        assert len(manifest.documents) == 2

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_manifest(tmp_path / "missing.tar.gz")

    def test_no_manifest_raises(self, tmp_path: Path) -> None:
        # Create a tar.gz without manifest.json
        bad_pack = tmp_path / "bad.tar.gz"
        with tarfile.open(bad_pack, "w:gz") as tar:
            dummy = tmp_path / "dummy.txt"
            dummy.write_text("hello")
            tar.add(dummy, arcname="pack/dummy.txt")

        with pytest.raises(ValueError, match="No manifest.json"):
            read_manifest(bad_pack)


# ---------------------------------------------------------------------------
# extract_pack tests
# ---------------------------------------------------------------------------


class TestExtractPack:
    def test_extracts_files(self, built_pack: Path, tmp_path: Path) -> None:
        target = tmp_path / "extracted"
        manifest = extract_pack(built_pack, target)

        assert isinstance(manifest, PackManifest)
        assert manifest.name == "test-pack"

        # Check files were extracted
        assert (target / "test-pack" / "manifest.json").is_file()
        assert (target / "test-pack" / "documents" / "intro.md").is_file()
        assert (target / "test-pack" / "documents" / "guide.txt").is_file()

    def test_document_content_preserved(self, built_pack: Path, tmp_path: Path) -> None:
        target = tmp_path / "extracted"
        extract_pack(built_pack, target)

        content = (target / "test-pack" / "documents" / "intro.md").read_text(encoding="utf-8")
        assert "# Introduction" in content

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            extract_pack(tmp_path / "nope.tar.gz", tmp_path / "out")


# ---------------------------------------------------------------------------
# validate_pack tests
# ---------------------------------------------------------------------------


class TestValidatePack:
    def test_valid_pack(self, built_pack: Path) -> None:
        errors = validate_pack(built_pack)
        assert errors == []

    def test_missing_file(self, tmp_path: Path) -> None:
        errors = validate_pack(tmp_path / "missing.tar.gz")
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_not_tar_gz(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.tar.gz"
        bad.write_text("not a tar file")
        errors = validate_pack(bad)
        assert any("valid tar.gz" in e.lower() or "tar" in e.lower() for e in errors)

    def test_missing_manifest(self, tmp_path: Path) -> None:
        pack = tmp_path / "no-manifest.tar.gz"
        with tarfile.open(pack, "w:gz") as tar:
            f = tmp_path / "file.txt"
            f.write_text("hi")
            tar.add(f, arcname="pack/file.txt")

        errors = validate_pack(pack)
        assert any("manifest" in e.lower() for e in errors)

    def test_missing_document_in_archive(self, tmp_path: Path) -> None:
        """Manifest lists a document that isn't in the archive."""
        pack_dir = tmp_path / "staging" / "bad-pack"
        pack_dir.mkdir(parents=True)

        manifest = {
            "name": "bad-pack",
            "version": "1.0.0",
            "description": "missing doc",
            "documents": ["documents/ghost.txt"],
            "doc_count": 1,
            "created_at": "2026-01-01T00:00:00Z",
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))

        pack_path = tmp_path / "bad-pack.tar.gz"
        with tarfile.open(pack_path, "w:gz") as tar:
            tar.add(pack_dir, arcname="bad-pack")

        errors = validate_pack(pack_path)
        assert any("ghost.txt" in e for e in errors)

    def test_doc_count_mismatch(self, tmp_path: Path) -> None:
        pack_dir = tmp_path / "staging" / "cnt-pack"
        docs_dir = pack_dir / "documents"
        docs_dir.mkdir(parents=True)

        doc = docs_dir / "a.txt"
        doc.write_text("hello")

        manifest = {
            "name": "cnt-pack",
            "version": "1.0.0",
            "documents": ["documents/a.txt"],
            "doc_count": 5,  # wrong
            "created_at": "2026-01-01T00:00:00Z",
        }
        (pack_dir / "manifest.json").write_text(json.dumps(manifest))

        pack_path = tmp_path / "cnt.tar.gz"
        with tarfile.open(pack_path, "w:gz") as tar:
            tar.add(pack_dir, arcname="cnt-pack")

        errors = validate_pack(pack_path)
        assert any("doc_count" in e for e in errors)
