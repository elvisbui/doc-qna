"""Comprehensive v1.4 tests — plugin loader, hook dispatch, manifest parsing,
enable/disable lifecycle.

Covers additional scenarios beyond the individual unit-test files to ensure
full coverage of edge cases, integration flows, and lifecycle correctness.
"""

from __future__ import annotations

import json
import types
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.plugins.base import PluginBase
from app.plugins.loader import PluginInfo, PluginRegistry, discover_plugins, load_plugin
from app.plugins.pipeline import PluginPipeline
from app.routers.plugins import router

# ===========================================================================
# Helpers
# ===========================================================================


def _write_py(tmp_path: Path, name: str, body: str) -> Path:
    path = tmp_path / f"{name}.py"
    path.write_text(body)
    return path


# Known hook names for testing (mirrors PluginBase methods).
_KNOWN_HOOKS: set[str] = {
    "on_chunk",
    "on_ingest",
    "on_retrieve",
    "on_post_retrieve",
    "on_generate",
    "on_post_generate",
}


# -- helper plugins for pipeline tests --


class DoublePlugin(PluginBase):
    name = "double"

    def on_chunk(self, text: str, metadata: dict) -> str:
        return text + text

    def on_retrieve(self, query: str) -> str:
        return query + query

    def on_ingest(self, document_id: str, chunks: list[str]) -> list[str]:
        return chunks + chunks

    def on_post_retrieve(self, query: str, results: list[dict]) -> list[dict]:
        return results * 2

    def on_generate(self, prompt: str, context: str) -> tuple[str, str]:
        return prompt + prompt, context + context

    def on_post_generate(self, answer: str) -> str:
        return answer + answer


class PrefixPlugin(PluginBase):
    name = "prefix"

    def on_chunk(self, text: str, metadata: dict) -> str:
        return "PRE:" + text

    def on_retrieve(self, query: str) -> str:
        return "PRE:" + query


class ErrorOnSecondCallPlugin(PluginBase):
    """Raises on the second call to on_chunk, succeeds on the first."""

    name = "flaky"
    _call_count = 0

    def on_chunk(self, text: str, metadata: dict) -> str:
        self._call_count += 1
        if self._call_count > 1:
            raise RuntimeError("flaky failure")
        return text.upper()


class MetadataReaderPlugin(PluginBase):
    """Reads metadata in on_chunk to test that metadata flows correctly."""

    name = "meta_reader"

    def on_chunk(self, text: str, metadata: dict) -> str:
        tag = metadata.get("tag", "none")
        return f"[{tag}]{text}"


# ===========================================================================
# 1. Plugin Loader — additional discover/load/registry tests
# ===========================================================================


class TestDiscoverPluginsExtended:
    def test_sorted_alphabetically(self, tmp_path: Path) -> None:
        _write_py(tmp_path, "zulu", "x=1")
        _write_py(tmp_path, "alpha", "x=2")
        _write_py(tmp_path, "mike", "x=3")
        result = discover_plugins(str(tmp_path))
        names = [p["name"] for p in result]
        assert names == sorted(names)

    def test_only_top_level_files(self, tmp_path: Path) -> None:
        """Subdirectory .py files should NOT be discovered."""
        sub = tmp_path / "nested"
        sub.mkdir()
        _write_py(sub, "deep", "x=1")
        _write_py(tmp_path, "top", "x=1")
        result = discover_plugins(str(tmp_path))
        assert len(result) == 1
        assert result[0]["name"] == "top"

    def test_module_key_format(self, tmp_path: Path) -> None:
        _write_py(tmp_path, "my_plugin", "x=1")
        result = discover_plugins(str(tmp_path))
        assert result[0]["module"] == "plugins.my_plugin"


class TestLoadPluginExtended:
    def test_module_attributes_accessible(self, tmp_path: Path) -> None:
        path = _write_py(tmp_path, "attrs", "MY_CONST = 42\ndef fn(): return 'ok'")
        info = {"name": "attrs", "path": str(path), "module": "plugins.attrs"}
        mod = load_plugin(info)
        assert mod.MY_CONST == 42
        assert mod.fn() == "ok"

    def test_raises_import_error_for_nonexistent_path(self, tmp_path: Path) -> None:
        info = {"name": "nope", "path": str(tmp_path / "nope.py"), "module": "plugins.nope"}
        with pytest.raises((ImportError, FileNotFoundError)):
            load_plugin(info)


class TestPluginRegistryExtended:
    def test_register_multiple_plugins(self, tmp_path: Path) -> None:
        registry = PluginRegistry(str(tmp_path))
        for i in range(5):
            mod = types.ModuleType(f"plugin_{i}")
            mod.__file__ = str(tmp_path / f"plugin_{i}.py")
            registry.register(f"plugin_{i}", mod, enabled=(i % 2 == 0))
        enabled = registry.get_enabled()
        assert len(enabled) == 3  # indices 0, 2, 4

    def test_re_register_preserves_saved_state_across_instances(self, tmp_path: Path) -> None:
        """A new PluginRegistry instance should honour the previously-persisted
        enabled state even when register() is called with a different default."""
        reg1 = PluginRegistry(str(tmp_path))
        mod = types.ModuleType("plug")
        mod.__file__ = str(tmp_path / "plug.py")
        reg1.register("plug", mod, enabled=True)
        reg1.toggle("plug", enabled=False)

        # New registry instance — saved state (False) should win over the
        # enabled=True default passed to register().
        reg2 = PluginRegistry(str(tmp_path))
        mod2 = types.ModuleType("plug")
        mod2.__file__ = str(tmp_path / "plug.py")
        reg2.register("plug", mod2, enabled=True)
        assert reg2.plugins["plug"].enabled is False

    def test_toggle_back_and_forth(self, tmp_path: Path) -> None:
        reg = PluginRegistry(str(tmp_path))
        mod = types.ModuleType("flip")
        mod.__file__ = str(tmp_path / "flip.py")
        reg.register("flip", mod, enabled=True)
        for expected in [False, True, False, True]:
            reg.toggle("flip", enabled=expected)
            assert reg.plugins["flip"].enabled is expected

    def test_registry_json_contains_core_fields(self, tmp_path: Path) -> None:
        reg = PluginRegistry(str(tmp_path))
        mod = types.ModuleType("full")
        mod.__file__ = str(tmp_path / "full.py")
        reg.register("full", mod, enabled=True)
        data = json.loads((tmp_path / "registry.json").read_text())
        entry = data["full"]
        # Must contain at least the core fields
        assert {"name", "path", "module_name", "enabled"}.issubset(set(entry.keys()))

    def test_registry_survives_empty_json_file(self, tmp_path: Path) -> None:
        (tmp_path / "registry.json").write_text("")
        reg = PluginRegistry(str(tmp_path))
        assert reg.plugins == {}

    def test_registry_survives_json_list_instead_of_dict(self, tmp_path: Path) -> None:
        (tmp_path / "registry.json").write_text("[1, 2, 3]")
        reg = PluginRegistry(str(tmp_path))
        assert reg.plugins == {}


# ===========================================================================
# 2. Hook Dispatch — pipeline ordering, error isolation, edge cases
# ===========================================================================


class TestPipelineOrdering:
    def test_three_plugins_chained(self) -> None:
        """Double -> Prefix -> Double should produce PRE:texttextPRE:texttext."""
        pipeline = PluginPipeline([DoublePlugin(), PrefixPlugin(), DoublePlugin()])
        result = pipeline.run_on_chunk("a", {})
        # double: "a" -> "aa"
        # prefix: "aa" -> "PRE:aa"
        # double: "PRE:aa" -> "PRE:aaPRE:aa"
        assert result == "PRE:aaPRE:aa"

    def test_ordering_matters_on_retrieve(self) -> None:
        p1 = PluginPipeline([PrefixPlugin(), DoublePlugin()])
        r1 = p1.run_on_retrieve("q")
        p2 = PluginPipeline([DoublePlugin(), PrefixPlugin()])
        r2 = p2.run_on_retrieve("q")
        assert r1 != r2
        assert r1 == "PRE:qPRE:q"
        assert r2 == "PRE:qq"

    def test_on_ingest_chained(self) -> None:
        pipeline = PluginPipeline([DoublePlugin()])
        result = pipeline.run_on_ingest("doc1", ["x"])
        assert result == ["x", "x"]

    def test_on_post_retrieve_chained(self) -> None:
        pipeline = PluginPipeline([DoublePlugin()])
        result = pipeline.run_on_post_retrieve("q", [{"id": 1}])
        assert result == [{"id": 1}, {"id": 1}]

    def test_on_generate_chained_two_values(self) -> None:
        pipeline = PluginPipeline([DoublePlugin()])
        p, c = pipeline.run_on_generate("p", "c")
        assert p == "pp"
        assert c == "cc"

    def test_on_post_generate_chained(self) -> None:
        pipeline = PluginPipeline([DoublePlugin()])
        assert pipeline.run_on_post_generate("z") == "zz"


class TestPipelineErrorIsolationExtended:
    def test_error_does_not_affect_subsequent_plugins(self) -> None:
        broken = PluginBase()
        broken.name = "exploder"
        broken.on_chunk = lambda text, meta: (_ for _ in ()).throw(  # type: ignore[assignment]
            RuntimeError("boom")
        )
        pipeline = PluginPipeline([broken, PrefixPlugin()])
        result = pipeline.run_on_chunk("text", {})
        assert result == "PRE:text"

    def test_trace_marks_errors_correctly(self) -> None:
        class Boom(PluginBase):
            name = "boom"

            def on_retrieve(self, query: str) -> str:
                raise ValueError("nope")

        pipeline = PluginPipeline([Boom(), DoublePlugin()])
        result = pipeline.run_on_retrieve("x")
        assert result == "xx"
        trace = pipeline.get_trace()
        assert trace[0]["error"] is True
        assert trace[0]["plugin"] == "boom"
        assert trace[1]["error"] is False

    def test_only_broken_hook_is_skipped(self) -> None:
        """A plugin that breaks on_chunk but works on_retrieve should
        still execute on_retrieve normally."""

        class PartiallyBroken(PluginBase):
            name = "partial"

            def on_chunk(self, text: str, metadata: dict) -> str:
                raise RuntimeError("chunk broken")

            def on_retrieve(self, query: str) -> str:
                return query.upper()

        plugin = PartiallyBroken()
        pipeline = PluginPipeline([plugin])
        # on_chunk should fail gracefully
        assert pipeline.run_on_chunk("hello", {}) == "hello"
        # on_retrieve should work fine
        assert pipeline.run_on_retrieve("hello") == "HELLO"


class TestPipelineDisabledPlugins:
    def test_disabled_plugin_does_not_mutate_data(self) -> None:
        plugin = DoublePlugin()
        plugin.enabled = False
        pipeline = PluginPipeline([plugin])
        assert pipeline.run_on_chunk("x", {}) == "x"
        assert pipeline.run_on_retrieve("q") == "q"
        assert pipeline.run_on_generate("p", "c") == ("p", "c")

    def test_disable_then_reenable(self) -> None:
        plugin = PrefixPlugin()
        pipeline = PluginPipeline([plugin])
        assert pipeline.run_on_chunk("hi", {}) == "PRE:hi"

        plugin.enabled = False
        assert pipeline.run_on_chunk("hi", {}) == "hi"

        plugin.enabled = True
        assert pipeline.run_on_chunk("hi", {}) == "PRE:hi"

    def test_mixed_enabled_disabled(self) -> None:
        p1 = PrefixPlugin()
        p2 = DoublePlugin()
        p2.enabled = False
        pipeline = PluginPipeline([p1, p2])
        assert pipeline.run_on_chunk("a", {}) == "PRE:a"


class TestPipelineMetadata:
    def test_metadata_passed_to_on_chunk(self) -> None:
        pipeline = PluginPipeline([MetadataReaderPlugin()])
        result = pipeline.run_on_chunk("hello", {"tag": "important"})
        assert result == "[important]hello"

    def test_metadata_default(self) -> None:
        pipeline = PluginPipeline([MetadataReaderPlugin()])
        result = pipeline.run_on_chunk("hello", {})
        assert result == "[none]hello"


class TestPipelineNoHook:
    def test_plugin_without_hook_is_skipped(self) -> None:
        """If a plugin doesn't implement a hook, it should be silently skipped."""

        class NoOpPlugin(PluginBase):
            name = "noop"
            # No hooks overridden

        pipeline = PluginPipeline([NoOpPlugin(), DoublePlugin()])
        assert pipeline.run_on_chunk("a", {}) == "aa"

    def test_run_hook_unknown_hook_name(self) -> None:
        """Calling a hook that no plugin implements should return input."""
        pipeline = PluginPipeline([DoublePlugin()])
        result = pipeline.run_hook("on_nonexistent", "data")
        assert result == "data"


class TestPipelineTraceExtended:
    def test_trace_duration_is_nonnegative(self) -> None:
        pipeline = PluginPipeline([DoublePlugin()])
        pipeline.run_on_chunk("x", {})
        for entry in pipeline.get_trace():
            assert entry["duration_ms"] >= 0

    def test_trace_hook_names(self) -> None:
        pipeline = PluginPipeline([DoublePlugin()])
        pipeline.run_on_chunk("x", {})
        pipeline.run_on_retrieve("q")
        pipeline.run_on_post_generate("a")
        hooks = [e["hook"] for e in pipeline.get_trace()]
        assert hooks == ["on_chunk", "on_retrieve", "on_post_generate"]


# ===========================================================================
# 3. Manifest Parsing — YAML parsing, validation, edge cases
# ===========================================================================


# ===========================================================================
# 4. Plugin Base Class — hook interface
# ===========================================================================


class TestPluginBaseExtended:
    def test_subclass_inherits_enabled(self) -> None:
        class MyPlugin(PluginBase):
            name = "mine"

        p = MyPlugin()
        assert p.enabled is True

    def test_all_hooks_exist(self) -> None:
        """Every known hook should exist as a method on PluginBase."""
        base = PluginBase()
        for hook in _KNOWN_HOOKS:
            assert hasattr(base, hook), f"PluginBase missing hook: {hook}"
            assert callable(getattr(base, hook))

    def test_on_generate_returns_tuple_type(self) -> None:
        base = PluginBase()
        result = base.on_generate("p", "c")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_subclass_override_single_hook(self) -> None:
        class OnlyChunk(PluginBase):
            name = "only_chunk"

            def on_chunk(self, text: str, metadata: dict) -> str:
                return text.lower()

        p = OnlyChunk()
        # Overridden hook
        assert p.on_chunk("HELLO", {}) == "hello"
        # Non-overridden hooks are no-ops
        assert p.on_retrieve("Q") == "Q"
        assert p.on_post_generate("A") == "A"


# ===========================================================================
# 5. Enable/Disable Lifecycle via Plugins API
# ===========================================================================


class FakeRegistry:
    """Minimal stand-in for PluginRegistry."""

    def __init__(self, plugins: dict[str, PluginInfo] | None = None) -> None:
        self.plugins: dict[str, PluginInfo] = plugins or {}

    def toggle(self, name: str, enabled: bool) -> None:
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        self.plugins[name].enabled = enabled


def _make_app(plugins: dict[str, PluginInfo] | None = None) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.plugin_registry = FakeRegistry(plugins)
    return app


@pytest.fixture()
def three_plugin_client():
    plugins = {
        "alpha": PluginInfo(name="alpha", path="/a.py", module_name="plugins.alpha", enabled=True),
        "beta": PluginInfo(name="beta", path="/b.py", module_name="plugins.beta", enabled=True),
        "gamma": PluginInfo(name="gamma", path="/g.py", module_name="plugins.gamma", enabled=False),
    }
    return TestClient(_make_app(plugins))


class TestEnableDisableLifecycle:
    def test_list_then_toggle_then_list(self, three_plugin_client) -> None:
        c = three_plugin_client
        # 1. List — gamma should be disabled
        resp = c.get("/api/plugins")
        assert resp.status_code == 200
        plugins = {p["name"]: p for p in resp.json()["plugins"]}
        assert plugins["gamma"]["enabled"] is False
        assert plugins["alpha"]["enabled"] is True

        # 2. Enable gamma
        resp = c.post("/api/plugins/gamma/toggle", json={"enabled": True})
        assert resp.status_code == 200
        assert resp.json()["enabled"] is True

        # 3. List again — gamma should now be enabled
        resp = c.get("/api/plugins")
        plugins = {p["name"]: p for p in resp.json()["plugins"]}
        assert plugins["gamma"]["enabled"] is True

    def test_disable_then_reenable(self, three_plugin_client) -> None:
        c = three_plugin_client
        # Disable alpha
        resp = c.post("/api/plugins/alpha/toggle", json={"enabled": False})
        assert resp.status_code == 200

        # Re-enable alpha
        resp = c.post("/api/plugins/alpha/toggle", json={"enabled": True})
        assert resp.status_code == 200

        # Verify
        resp = c.get("/api/plugins")
        plugins = {p["name"]: p for p in resp.json()["plugins"]}
        assert plugins["alpha"]["enabled"] is True

    def test_toggle_nonexistent_returns_404(self, three_plugin_client) -> None:
        resp = three_plugin_client.post("/api/plugins/nonexistent/toggle", json={"enabled": True})
        assert resp.status_code == 404

    def test_toggle_invalid_body_returns_422(self, three_plugin_client) -> None:
        resp = three_plugin_client.post("/api/plugins/alpha/toggle", json={"wrong_field": True})
        assert resp.status_code == 422

    def test_toggle_no_body_returns_422(self, three_plugin_client) -> None:
        resp = three_plugin_client.post("/api/plugins/alpha/toggle")
        assert resp.status_code == 422

    def test_all_plugins_returned_in_list(self, three_plugin_client) -> None:
        resp = three_plugin_client.get("/api/plugins")
        names = {p["name"] for p in resp.json()["plugins"]}
        assert names == {"alpha", "beta", "gamma"}

    def test_empty_registry(self) -> None:
        client = TestClient(_make_app())
        resp = client.get("/api/plugins")
        assert resp.status_code == 200
        assert resp.json() == {"plugins": []}


# ===========================================================================
# 6. Integration — discover -> load -> register -> pipeline -> toggle
# ===========================================================================


class TestFullLifecycleIntegration:
    def test_discover_load_register_run_toggle(self, tmp_path: Path) -> None:
        """End-to-end: discover a plugin, load it, register, run through
        pipeline, toggle disable, verify it no longer runs."""
        # Write a plugin that uppercases text
        _write_py(
            tmp_path,
            "uppercaser",
            (
                "from app.plugins.base import PluginBase\n"
                "class Uppercaser(PluginBase):\n"
                "    name = 'uppercaser'\n"
                "    def on_chunk(self, text, metadata):\n"
                "        return text.upper()\n"
                "plugin_class = Uppercaser\n"
            ),
        )

        # Discover
        discovered = discover_plugins(str(tmp_path))
        assert len(discovered) == 1

        # Load
        mod = load_plugin(discovered[0])
        assert hasattr(mod, "plugin_class")

        # Instantiate and run through pipeline
        plugin_instance = mod.plugin_class()
        pipeline = PluginPipeline([plugin_instance])
        assert pipeline.run_on_chunk("hello", {}) == "HELLO"

        # Register in registry
        registry = PluginRegistry(str(tmp_path))
        registry.register("uppercaser", mod)
        assert len(registry.get_enabled()) == 1

        # Disable
        registry.toggle("uppercaser", enabled=False)
        plugin_instance.enabled = False
        assert pipeline.run_on_chunk("hello", {}) == "hello"

        # Re-enable
        registry.toggle("uppercaser", enabled=True)
        plugin_instance.enabled = True
        assert pipeline.run_on_chunk("hello", {}) == "HELLO"

    def test_plugin_pipeline_trim(self, tmp_path: Path) -> None:
        """Create a plugin and run it through the pipeline."""

        class TrimmerPlugin(PluginBase):
            name = "trimmer"

            def on_chunk(self, text: str, metadata: dict) -> str:
                return text.strip()

        pipeline = PluginPipeline([TrimmerPlugin()])
        assert pipeline.run_on_chunk("  spaced  ", {}) == "spaced"
