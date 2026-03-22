"""Tests for the plugin loader — discovery, loading, and registry."""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest

from app.plugins.loader import PluginRegistry, discover_plugins, load_plugin

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_plugin(plugins_dir: Path, name: str, body: str) -> Path:
    """Write a plugin file into *plugins_dir* and return its path."""
    path = plugins_dir / f"{name}.py"
    path.write_text(body)
    return path


GOOD_PLUGIN = """\
registered = False

def register(app):
    global registered
    registered = True
"""

BAD_PLUGIN = """\
raise RuntimeError("intentional error during import")
"""


# ---------------------------------------------------------------------------
# discover_plugins
# ---------------------------------------------------------------------------


class TestDiscoverPlugins:
    def test_empty_directory(self, tmp_path: Path) -> None:
        assert discover_plugins(str(tmp_path)) == []

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        assert discover_plugins(str(tmp_path / "does_not_exist")) == []

    def test_discovers_py_files(self, tmp_path: Path) -> None:
        _write_plugin(tmp_path, "alpha", GOOD_PLUGIN)
        _write_plugin(tmp_path, "beta", GOOD_PLUGIN)
        result = discover_plugins(str(tmp_path))
        names = [p["name"] for p in result]
        assert "alpha" in names
        assert "beta" in names
        assert len(result) == 2

    def test_ignores_underscore_files(self, tmp_path: Path) -> None:
        _write_plugin(tmp_path, "_hidden", GOOD_PLUGIN)
        _write_plugin(tmp_path, "__init__", "")
        _write_plugin(tmp_path, "visible", GOOD_PLUGIN)
        result = discover_plugins(str(tmp_path))
        assert len(result) == 1
        assert result[0]["name"] == "visible"

    def test_ignores_non_py_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("hello")
        (tmp_path / "data.json").write_text("{}")
        _write_plugin(tmp_path, "myplugin", GOOD_PLUGIN)
        result = discover_plugins(str(tmp_path))
        assert len(result) == 1

    def test_result_shape(self, tmp_path: Path) -> None:
        _write_plugin(tmp_path, "sample", GOOD_PLUGIN)
        result = discover_plugins(str(tmp_path))
        entry = result[0]
        assert set(entry.keys()) == {"name", "path", "module"}
        assert entry["name"] == "sample"
        assert entry["path"].endswith("sample.py")
        assert entry["module"] == "plugins.sample"


# ---------------------------------------------------------------------------
# load_plugin
# ---------------------------------------------------------------------------


class TestLoadPlugin:
    def test_loads_valid_module(self, tmp_path: Path) -> None:
        path = _write_plugin(tmp_path, "good", GOOD_PLUGIN)
        info = {"name": "good", "path": str(path), "module": "plugins.good"}
        mod = load_plugin(info)
        assert isinstance(mod, types.ModuleType)
        assert hasattr(mod, "register")

    def test_raises_on_bad_module(self, tmp_path: Path) -> None:
        path = _write_plugin(tmp_path, "bad", BAD_PLUGIN)
        info = {"name": "bad", "path": str(path), "module": "plugins.bad"}
        with pytest.raises(RuntimeError, match="intentional error"):
            load_plugin(info)

    def test_raises_on_missing_file(self, tmp_path: Path) -> None:
        info = {"name": "ghost", "path": str(tmp_path / "ghost.py"), "module": "plugins.ghost"}
        with pytest.raises((ImportError, FileNotFoundError)):
            load_plugin(info)


# ---------------------------------------------------------------------------
# PluginRegistry
# ---------------------------------------------------------------------------


class TestPluginRegistry:
    def test_register_and_get_enabled(self, tmp_path: Path) -> None:
        registry = PluginRegistry(str(tmp_path))
        mod = types.ModuleType("fake_plugin")
        mod.__file__ = str(tmp_path / "fake.py")
        registry.register("fake", mod, enabled=True)
        enabled = registry.get_enabled()
        assert len(enabled) == 1
        assert enabled[0].name == "fake"

    def test_toggle_disable(self, tmp_path: Path) -> None:
        registry = PluginRegistry(str(tmp_path))
        mod = types.ModuleType("toggler")
        mod.__file__ = str(tmp_path / "toggler.py")
        registry.register("toggler", mod, enabled=True)
        assert len(registry.get_enabled()) == 1
        registry.toggle("toggler", enabled=False)
        assert len(registry.get_enabled()) == 0

    def test_toggle_enable(self, tmp_path: Path) -> None:
        registry = PluginRegistry(str(tmp_path))
        mod = types.ModuleType("off")
        mod.__file__ = str(tmp_path / "off.py")
        registry.register("off", mod, enabled=False)
        assert len(registry.get_enabled()) == 0
        registry.toggle("off", enabled=True)
        assert len(registry.get_enabled()) == 1

    def test_toggle_unknown_raises(self, tmp_path: Path) -> None:
        registry = PluginRegistry(str(tmp_path))
        with pytest.raises(KeyError, match="not_there"):
            registry.toggle("not_there", enabled=False)

    def test_state_persisted_to_json(self, tmp_path: Path) -> None:
        registry = PluginRegistry(str(tmp_path))
        mod = types.ModuleType("persisted")
        mod.__file__ = str(tmp_path / "persisted.py")
        registry.register("persisted", mod, enabled=True)

        json_path = tmp_path / "registry.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert "persisted" in data
        assert data["persisted"]["enabled"] is True

    def test_state_restored_on_init(self, tmp_path: Path) -> None:
        # First registry — register and disable.
        r1 = PluginRegistry(str(tmp_path))
        mod = types.ModuleType("survivor")
        mod.__file__ = str(tmp_path / "survivor.py")
        r1.register("survivor", mod, enabled=True)
        r1.toggle("survivor", enabled=False)

        # Second registry — should restore disabled state.
        r2 = PluginRegistry(str(tmp_path))
        mod2 = types.ModuleType("survivor")
        mod2.__file__ = str(tmp_path / "survivor.py")
        r2.register("survivor", mod2, enabled=True)  # default True, but saved is False
        assert r2.plugins["survivor"].enabled is False

    def test_corrupted_registry_file(self, tmp_path: Path) -> None:
        (tmp_path / "registry.json").write_text("not json!!!")
        # Should not raise — just logs a warning and starts fresh.
        registry = PluginRegistry(str(tmp_path))
        assert registry.plugins == {}


# ---------------------------------------------------------------------------
# Integration: discover -> load -> register
# ---------------------------------------------------------------------------


class TestIntegration:
    def test_full_flow(self, tmp_path: Path) -> None:
        _write_plugin(tmp_path, "hello", GOOD_PLUGIN)
        discovered = discover_plugins(str(tmp_path))
        assert len(discovered) == 1

        mod = load_plugin(discovered[0])
        registry = PluginRegistry(str(tmp_path))
        registry.register("hello", mod)

        assert len(registry.get_enabled()) == 1
        assert registry.plugins["hello"].enabled is True

    def test_bad_plugin_skipped(self, tmp_path: Path) -> None:
        _write_plugin(tmp_path, "good_one", GOOD_PLUGIN)
        _write_plugin(tmp_path, "bad_one", BAD_PLUGIN)

        discovered = discover_plugins(str(tmp_path))
        registry = PluginRegistry(str(tmp_path))

        for pinfo in discovered:
            try:
                mod = load_plugin(pinfo)
                registry.register(pinfo["name"], mod)
            except Exception:
                pass  # skip broken plugins

        assert len(registry.plugins) == 1
        assert "good_one" in registry.plugins
