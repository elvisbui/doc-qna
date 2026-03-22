"""Tests for per-plugin config — base class, registry, and API endpoints."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.plugins.base import ConfigField, PluginBase
from app.plugins.loader import PluginInfo, PluginRegistry
from app.routers.plugins import router

# ---------------------------------------------------------------------------
# PluginBase config mechanism
# ---------------------------------------------------------------------------


class TestConfigFieldDefaults:
    def test_config_field_defaults(self):
        f = ConfigField(name="api_key")
        assert f.name == "api_key"
        assert f.field_type == "string"
        assert f.default == ""
        assert f.label == ""
        assert f.description == ""
        assert f.options is None


class ConfigurablePlugin(PluginBase):
    """Plugin with declared config fields for testing."""

    name = "configurable"
    description = "A plugin with config"
    config_fields = [
        ConfigField(name="threshold", field_type="number", default=0.5, label="Threshold"),
        ConfigField(name="mode", field_type="select", default="fast", label="Mode", options=["fast", "accurate"]),
        ConfigField(name="debug", field_type="boolean", default=False, label="Debug Mode"),
    ]


class TestPluginBaseConfig:
    def test_config_initialised_from_defaults(self):
        p = ConfigurablePlugin()
        assert p.config == {"threshold": 0.5, "mode": "fast", "debug": False}

    def test_get_config_schema(self):
        p = ConfigurablePlugin()
        schema = p.get_config_schema()
        assert len(schema) == 3
        assert schema[0]["name"] == "threshold"
        assert schema[0]["field_type"] == "number"
        assert schema[0]["default"] == 0.5
        assert schema[0]["label"] == "Threshold"
        assert schema[1]["options"] == ["fast", "accurate"]

    def test_update_config_valid_keys(self):
        p = ConfigurablePlugin()
        result = p.update_config({"threshold": 0.8, "mode": "accurate"})
        assert result["threshold"] == 0.8
        assert result["mode"] == "accurate"
        assert result["debug"] is False  # unchanged

    def test_update_config_ignores_unknown_keys(self):
        p = ConfigurablePlugin()
        result = p.update_config({"unknown_key": "value", "threshold": 0.9})
        assert "unknown_key" not in result
        assert result["threshold"] == 0.9

    def test_no_config_fields_by_default(self):
        p = PluginBase()
        assert p.config == {}
        assert p.get_config_schema() == []

    def test_update_config_empty_schema(self):
        p = PluginBase()
        result = p.update_config({"anything": 42})
        assert result == {}


# ---------------------------------------------------------------------------
# PluginRegistry config methods
# ---------------------------------------------------------------------------


class FakeRegistryWithConfig:
    """Minimal stand-in for PluginRegistry for config API tests."""

    def __init__(self, plugins: dict[str, PluginInfo] | None = None) -> None:
        self.plugins: dict[str, PluginInfo] = plugins or {}

    def toggle(self, name: str, enabled: bool) -> None:
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        self.plugins[name].enabled = enabled

    def get_config(self, name: str) -> dict:
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        return {
            "config": dict(self.plugins[name].config),
            "config_schema": list(self.plugins[name].config_schema),
        }

    def update_config(self, name: str, values: dict) -> dict:
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        info = self.plugins[name]
        valid_keys = {f["name"] for f in info.config_schema}
        for key, value in values.items():
            if key in valid_keys:
                info.config[key] = value
        return dict(info.config)


SAMPLE_SCHEMA = [
    {"name": "threshold", "field_type": "number", "default": 0.5, "label": "Threshold", "description": ""},
    {
        "name": "mode",
        "field_type": "select",
        "default": "fast",
        "label": "Mode",
        "description": "",
        "options": ["fast", "accurate"],
    },
]


@pytest.fixture()
def app_with_config():
    app = FastAPI()
    app.include_router(router)
    registry = FakeRegistryWithConfig(
        {
            "configurable": PluginInfo(
                name="configurable",
                path="/fake/configurable.py",
                module_name="plugins.configurable",
                enabled=True,
                config={"threshold": 0.5, "mode": "fast"},
                config_schema=SAMPLE_SCHEMA,
            ),
            "no_config": PluginInfo(
                name="no_config",
                path="/fake/no_config.py",
                module_name="plugins.no_config",
                enabled=True,
                config={},
                config_schema=[],
            ),
        }
    )
    app.state.plugin_registry = registry
    return app


@pytest.fixture()
def client(app_with_config):
    return TestClient(app_with_config)


# -- GET /api/plugins/{name}/config -----------------------------------------


class TestGetPluginConfig:
    def test_returns_config_and_schema(self, client):
        resp = client.get("/api/plugins/configurable/config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "configurable"
        assert body["config"] == {"threshold": 0.5, "mode": "fast"}
        assert len(body["configSchema"]) == 2

    def test_empty_config(self, client):
        resp = client.get("/api/plugins/no_config/config")
        assert resp.status_code == 200
        body = resp.json()
        assert body["config"] == {}
        assert body["configSchema"] == []

    def test_not_found(self, client):
        resp = client.get("/api/plugins/nonexistent/config")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# -- PUT /api/plugins/{name}/config -----------------------------------------


class TestUpdatePluginConfig:
    def test_updates_valid_keys(self, client):
        resp = client.put(
            "/api/plugins/configurable/config",
            json={"config": {"threshold": 0.9}},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "configurable"
        assert body["config"]["threshold"] == 0.9
        assert body["config"]["mode"] == "fast"  # unchanged

    def test_ignores_unknown_keys(self, client):
        resp = client.put(
            "/api/plugins/configurable/config",
            json={"config": {"unknown": "val", "threshold": 0.7}},
        )
        assert resp.status_code == 200
        assert "unknown" not in resp.json()["config"]
        assert resp.json()["config"]["threshold"] == 0.7

    def test_not_found(self, client):
        resp = client.put(
            "/api/plugins/nonexistent/config",
            json={"config": {"x": 1}},
        )
        assert resp.status_code == 404

    def test_missing_body(self, client):
        resp = client.put("/api/plugins/configurable/config")
        assert resp.status_code == 422


# -- PluginRegistry.get_config / update_config on real registry ---------------


class TestRegistryConfig:
    def test_get_config(self, tmp_path: Path):
        registry = PluginRegistry(str(tmp_path))
        info = PluginInfo(
            name="test",
            path="/fake.py",
            module_name="plugins.test",
            config={"a": 1},
            config_schema=[{"name": "a", "field_type": "number", "default": 0, "label": "A", "description": ""}],
        )
        registry.plugins["test"] = info
        result = registry.get_config("test")
        assert result["config"] == {"a": 1}
        assert len(result["config_schema"]) == 1

    def test_get_config_not_found(self, tmp_path: Path):
        registry = PluginRegistry(str(tmp_path))
        with pytest.raises(KeyError):
            registry.get_config("missing")

    def test_update_config(self, tmp_path: Path):
        registry = PluginRegistry(str(tmp_path))
        info = PluginInfo(
            name="test",
            path="/fake.py",
            module_name="plugins.test",
            config={"a": 1, "b": "hello"},
            config_schema=[
                {"name": "a", "field_type": "number", "default": 0, "label": "A", "description": ""},
                {"name": "b", "field_type": "string", "default": "", "label": "B", "description": ""},
            ],
        )
        registry.plugins["test"] = info
        result = registry.update_config("test", {"a": 42, "unknown": "x"})
        assert result["a"] == 42
        assert result["b"] == "hello"
        assert "unknown" not in result

    def test_update_config_persists(self, tmp_path: Path):
        registry = PluginRegistry(str(tmp_path))
        info = PluginInfo(
            name="test",
            path="/fake.py",
            module_name="plugins.test",
            config={"val": 1},
            config_schema=[{"name": "val", "field_type": "number", "default": 0, "label": "V", "description": ""}],
        )
        registry.plugins["test"] = info
        registry.update_config("test", {"val": 99})
        # Read back the persisted JSON
        data = json.loads((tmp_path / "registry.json").read_text())
        assert data["test"]["config"]["val"] == 99

    def test_update_config_not_found(self, tmp_path: Path):
        registry = PluginRegistry(str(tmp_path))
        with pytest.raises(KeyError):
            registry.update_config("missing", {"x": 1})


# -- config_schema in list_plugins response ---------------------------------


class TestListPluginsIncludesSchema:
    def test_config_schema_in_list(self, client):
        resp = client.get("/api/plugins")
        assert resp.status_code == 200
        plugins = resp.json()["plugins"]
        configurable = next(p for p in plugins if p["name"] == "configurable")
        assert "configSchema" in configurable
        assert len(configurable["configSchema"]) == 2
