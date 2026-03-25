"""Tests for the Plugins API (GET /api/plugins, POST /api/plugins/{name}/toggle)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.plugins.loader import PluginInfo
from app.routers.plugins import router


class FakeRegistry:
    """Minimal stand-in for PluginRegistry used in tests."""

    def __init__(self, plugins: dict[str, PluginInfo] | None = None) -> None:
        self.plugins: dict[str, PluginInfo] = plugins or {}

    def toggle(self, name: str, enabled: bool) -> None:
        if name not in self.plugins:
            raise KeyError(f"Plugin '{name}' is not registered")
        self.plugins[name].enabled = enabled


@pytest.fixture()
def app_with_plugins():
    """Create a FastAPI app with a fake plugin registry on app.state."""
    app = FastAPI()
    app.include_router(router)

    registry = FakeRegistry(
        {
            "summarizer": PluginInfo(
                name="summarizer",
                path="/fake/summarizer.py",
                module_name="plugins.summarizer",
                enabled=True,
            ),
            "reranker": PluginInfo(
                name="reranker",
                path="/fake/reranker.py",
                module_name="plugins.reranker",
                enabled=False,
            ),
        }
    )
    app.state.plugin_registry = registry
    return app


@pytest.fixture()
def client(app_with_plugins):
    return TestClient(app_with_plugins)


# ── GET /api/plugins ────────────────────────────────────────────────


def test_list_plugins_returns_all(client):
    resp = client.get("/api/plugins")
    assert resp.status_code == 200
    data = resp.json()
    assert "plugins" in data
    names = {p["name"] for p in data["plugins"]}
    assert names == {"summarizer", "reranker"}


def test_list_plugins_fields(client):
    resp = client.get("/api/plugins")
    plugin = resp.json()["plugins"][0]
    assert "name" in plugin
    assert "description" in plugin
    assert "version" in plugin
    assert "enabled" in plugin
    assert "hooks" in plugin
    assert isinstance(plugin["hooks"], list)
    assert isinstance(plugin["enabled"], bool)


def test_list_plugins_empty():
    app = FastAPI()
    app.include_router(router)
    app.state.plugin_registry = FakeRegistry()
    c = TestClient(app)
    resp = c.get("/api/plugins")
    assert resp.status_code == 200
    assert resp.json() == {"plugins": []}


# ── POST /api/plugins/{name}/toggle ─────────────────────────────────


def test_toggle_enable_plugin(client):
    resp = client.post("/api/plugins/reranker/toggle", json={"enabled": True})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"name": "reranker", "enabled": True}


def test_toggle_disable_plugin(client):
    resp = client.post("/api/plugins/summarizer/toggle", json={"enabled": False})
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"name": "summarizer", "enabled": False}


def test_toggle_not_found(client):
    resp = client.post("/api/plugins/nonexistent/toggle", json={"enabled": True})
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_toggle_persists_in_registry(app_with_plugins):
    c = TestClient(app_with_plugins)
    c.post("/api/plugins/summarizer/toggle", json={"enabled": False})
    registry = app_with_plugins.state.plugin_registry
    assert registry.plugins["summarizer"].enabled is False


def test_toggle_missing_body(client):
    resp = client.post("/api/plugins/summarizer/toggle")
    assert resp.status_code == 422
