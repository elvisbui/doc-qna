"""Knowledge pack registry — discover, index, and track installed packs."""

from __future__ import annotations

import json
import logging
import tarfile
from pathlib import Path

from app.packs.models import PackManifest

logger = logging.getLogger(__name__)


class PackRegistry:
    """Discovers pack directories and archives, maintains an install-state index.

    The registry persists its state to ``registry.json`` inside the packs
    directory so that install/uninstall status survives restarts.
    """

    def __init__(self, packs_dir: str | Path) -> None:
        self._packs_dir = Path(packs_dir)
        self._state_file = self._packs_dir / "registry.json"
        self._installed: set[str] = set()
        self._versions: dict[str, str] = {}
        self._manifests: list[PackManifest] = []
        self._suggested_queries: dict[str, list[str]] = {}
        self._load_state()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def scan_local(self, packs_dir: str | None = None) -> list[PackManifest]:
        """Discover pack directories and ``.tar.gz`` files in *packs_dir*.

        Args:
            packs_dir: Override the directory to scan.  Defaults to the
                directory the registry was initialised with.

        Returns:
            A list of discovered ``PackManifest`` objects.
        """
        scan_path = Path(packs_dir) if packs_dir else self._packs_dir
        manifests: list[PackManifest] = []

        if not scan_path.is_dir():
            self._manifests = manifests
            return manifests

        suggested: dict[str, list[str]] = {}
        for entry in sorted(scan_path.iterdir()):
            manifest = self._try_load(entry)
            if manifest is not None:
                manifests.append(manifest)
                queries = self._try_load_suggested_queries(entry)
                if queries:
                    suggested[manifest.name] = queries

        self._manifests = manifests
        self._suggested_queries = suggested
        return manifests

    def get_index(self) -> list[dict]:
        """Return a registry index with key metadata for every discovered pack.

        Each dict contains: ``name``, ``version``, ``description``,
        ``doc_count``, and ``installed`` (bool).

        If :meth:`scan_local` has not been called yet, it is called
        automatically with the default packs directory.
        """
        if not self._manifests:
            self.scan_local()

        index: list[dict] = []
        for m in self._manifests:
            index.append(
                {
                    "name": m.name,
                    "version": m.version,
                    "description": m.description,
                    "doc_count": m.doc_count,
                    "installed": m.name in self._installed,
                    "installed_version": self._versions.get(m.name),
                    "suggested_queries": self._suggested_queries.get(m.name, []),
                }
            )
        return index

    def mark_installed(self, name: str, version: str | None = None) -> None:
        """Record that the pack *name* has been installed.

        Args:
            name: Pack identifier.
            version: Optional semantic version string to track.
        """
        self._installed.add(name)
        if version is not None:
            self._versions[name] = version
        self._save_state()

    def mark_uninstalled(self, name: str) -> None:
        """Record that the pack *name* has been uninstalled."""
        self._installed.discard(name)
        self._versions.pop(name, None)
        self._save_state()

    def get_installed_version(self, name: str) -> str | None:
        """Return the installed version of *name*, or ``None`` if not installed."""
        if name not in self._installed:
            return None
        return self._versions.get(name)

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _load_state(self) -> None:
        """Load previously persisted install state from ``registry.json``.

        Handles both the legacy format (``installed`` is a list of names) and
        the new format (``installed`` is a list, ``versions`` is a dict).
        """
        if self._state_file.is_file():
            try:
                data = json.loads(self._state_file.read_text(encoding="utf-8"))
                self._installed = set(data.get("installed", []))
                self._versions = dict(data.get("versions", {}))
            except (json.JSONDecodeError, OSError):
                self._installed = set()
                self._versions = {}

    def _save_state(self) -> None:
        """Persist current install state to ``registry.json``."""
        self._packs_dir.mkdir(parents=True, exist_ok=True)
        data = {
            "installed": sorted(self._installed),
            "versions": self._versions,
        }
        self._state_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Discovery helpers
    # ------------------------------------------------------------------

    def _try_load(self, entry: Path) -> PackManifest | None:
        """Attempt to load a manifest from a directory or ``.tar.gz`` file."""
        if entry.is_dir():
            return self._load_from_directory(entry)
        if entry.name.endswith(".tar.gz"):
            return self._load_from_archive(entry)
        return None

    def _try_load_suggested_queries(self, entry: Path) -> list[str]:
        """Load suggested queries from a directory or archive."""
        if entry.is_dir():
            return self._load_queries_from_directory(entry)
        if entry.name.endswith(".tar.gz"):
            return self._load_queries_from_archive(entry)
        return []

    @staticmethod
    def _load_queries_from_directory(path: Path) -> list[str]:
        """Load suggested queries from a pack directory."""
        queries_path = path / "suggested_queries.json"
        if not queries_path.is_file():
            return []
        try:
            data = json.loads(queries_path.read_text(encoding="utf-8"))
            return list(data.get("queries", []))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load queries from %s: %s", queries_path, exc)
            return []

    @staticmethod
    def _load_queries_from_archive(path: Path) -> list[str]:
        """Load suggested queries from a ``.tar.gz`` archive."""
        try:
            with tarfile.open(path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("suggested_queries.json") and member.isfile():
                        f = tar.extractfile(member)
                        if f is not None:
                            data = json.loads(f.read())
                            return list(data.get("queries", []))
        except (tarfile.TarError, json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load queries from archive %s: %s", path, exc)
            return []
        return []

    @staticmethod
    def _load_from_directory(path: Path) -> PackManifest | None:
        """Load a ``PackManifest`` from a pack directory."""
        manifest_path = path / "manifest.json"
        if not manifest_path.is_file():
            return None
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            return PackManifest(**data)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load manifest from %s: %s", manifest_path, exc)
            return None

    @staticmethod
    def _load_from_archive(path: Path) -> PackManifest | None:
        """Load a ``PackManifest`` from a ``.tar.gz`` archive."""
        try:
            with tarfile.open(path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("manifest.json") and member.isfile():
                        f = tar.extractfile(member)
                        if f is not None:
                            data = json.loads(f.read())
                            return PackManifest(**data)
        except (tarfile.TarError, json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to load manifest from archive %s: %s", path, exc)
            return None
        return None
