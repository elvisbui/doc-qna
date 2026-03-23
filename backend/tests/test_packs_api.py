"""Tests for the Packs API (GET /api/packs, POST /api/packs/{id}/install)."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.packs.models import PackManifest
from app.packs.registry import PackRegistry
from app.routers.packs import router


@pytest.fixture()
def packs_dir(tmp_path: Path) -> Path:
    """Create a temporary packs directory with two sample packs."""
    pack1_dir = tmp_path / "python-docs"
    pack1_dir.mkdir()
    manifest1 = {
        "name": "python-docs",
        "version": "1.0.0",
        "description": "Python documentation pack",
        "doc_count": 5,
        "documents": [],
    }
    (pack1_dir / "manifest.json").write_text(json.dumps(manifest1))

    pack2_dir = tmp_path / "fastapi-docs"
    pack2_dir.mkdir()
    manifest2 = {
        "name": "fastapi-docs",
        "version": "2.1.0",
        "description": "FastAPI documentation pack",
        "doc_count": 3,
        "documents": [],
    }
    (pack2_dir / "manifest.json").write_text(json.dumps(manifest2))

    return tmp_path


@pytest.fixture()
def registry(packs_dir: Path) -> PackRegistry:
    """Create a PackRegistry from the temp packs directory."""
    reg = PackRegistry(packs_dir)
    reg.scan_local()
    return reg


@pytest.fixture()
def app_with_packs(registry: PackRegistry) -> FastAPI:
    """Create a FastAPI app with a pack registry on app.state."""
    app = FastAPI()
    app.include_router(router)
    app.state.pack_registry = registry
    return app


@pytest.fixture()
def client(app_with_packs: FastAPI) -> TestClient:
    return TestClient(app_with_packs)


# ── GET /api/packs ────────────────────────────────────────────────


def test_list_packs_returns_all(client: TestClient) -> None:
    resp = client.get("/api/packs")
    assert resp.status_code == 200
    data = resp.json()
    assert "packs" in data
    names = {p["name"] for p in data["packs"]}
    assert names == {"python-docs", "fastapi-docs"}


def test_list_packs_fields(client: TestClient) -> None:
    resp = client.get("/api/packs")
    pack = resp.json()["packs"][0]
    assert "name" in pack
    assert "version" in pack
    assert "description" in pack
    assert "docCount" in pack
    assert "installed" in pack
    assert isinstance(pack["installed"], bool)
    assert isinstance(pack["docCount"], int)


def test_list_packs_empty() -> None:
    with tempfile.TemporaryDirectory() as d:
        reg = PackRegistry(d)
        reg.scan_local()
        app = FastAPI()
        app.include_router(router)
        app.state.pack_registry = reg
        c = TestClient(app)
        resp = c.get("/api/packs")
        assert resp.status_code == 200
        assert resp.json() == {"packs": []}


def test_list_packs_shows_installed_status(registry: PackRegistry, app_with_packs: FastAPI) -> None:
    registry.mark_installed("python-docs")
    c = TestClient(app_with_packs)
    resp = c.get("/api/packs")
    packs_data = {p["name"]: p for p in resp.json()["packs"]}
    assert packs_data["python-docs"]["installed"] is True
    assert packs_data["fastapi-docs"]["installed"] is False


# ── POST /api/packs/{id}/install ─────────────────────────────────


def test_install_pack_not_found(client: TestClient) -> None:
    resp = client.post("/api/packs/nonexistent/install")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_install_pack_already_installed(registry: PackRegistry, app_with_packs: FastAPI) -> None:
    registry.mark_installed("python-docs")
    c = TestClient(app_with_packs)
    resp = c.post("/api/packs/python-docs/install")
    assert resp.status_code == 409
    assert "already installed" in resp.json()["detail"].lower()


def test_install_pack_success(
    packs_dir: Path,
    registry: PackRegistry,
    app_with_packs: FastAPI,
) -> None:
    """Successful install returns pack details with installed=True."""
    manifest = PackManifest(
        name="python-docs",
        version="1.0.0",
        description="Python documentation pack",
        doc_count=5,
    )

    async def fake_install(pack_path, settings, registry=None):
        if registry:
            registry.mark_installed("python-docs")
        return manifest

    mock_settings = MagicMock(PACKS_DIR=str(packs_dir))

    with (
        patch("app.routers.packs.get_settings", return_value=mock_settings),
        patch("app.routers.packs.do_install", new=AsyncMock(side_effect=fake_install)),
    ):
        c = TestClient(app_with_packs)
        resp = c.post("/api/packs/python-docs/install")

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "python-docs"
    assert body["version"] == "1.0.0"
    assert body["installed"] is True


def test_install_pack_validation_error(
    packs_dir: Path,
    registry: PackRegistry,
    app_with_packs: FastAPI,
) -> None:
    """Install that raises ValueError returns 422."""
    mock_settings = MagicMock(PACKS_DIR=str(packs_dir))

    with (
        patch("app.routers.packs.get_settings", return_value=mock_settings),
        patch(
            "app.routers.packs.do_install",
            new=AsyncMock(side_effect=ValueError("Invalid pack: missing manifest")),
        ),
    ):
        c = TestClient(app_with_packs)
        resp = c.post("/api/packs/python-docs/install")

    assert resp.status_code == 422
    assert "invalid pack" in resp.json()["detail"].lower()


# ── Suggested queries ────────────────────────────────────────────


@pytest.fixture()
def packs_dir_with_queries(tmp_path: Path) -> Path:
    """Create packs directory where one pack has suggested_queries.json."""
    pack1_dir = tmp_path / "python-docs"
    pack1_dir.mkdir()
    (pack1_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "python-docs",
                "version": "1.0.0",
                "description": "Python documentation pack",
                "doc_count": 5,
                "documents": [],
            }
        )
    )
    (pack1_dir / "suggested_queries.json").write_text(
        json.dumps(
            {
                "queries": [
                    "What are Python decorators?",
                    "How do list comprehensions work?",
                ]
            }
        )
    )

    pack2_dir = tmp_path / "fastapi-docs"
    pack2_dir.mkdir()
    (pack2_dir / "manifest.json").write_text(
        json.dumps(
            {
                "name": "fastapi-docs",
                "version": "2.1.0",
                "description": "FastAPI documentation pack",
                "doc_count": 3,
                "documents": [],
            }
        )
    )
    # No suggested_queries.json for pack2

    return tmp_path


@pytest.fixture()
def registry_with_queries(packs_dir_with_queries: Path) -> PackRegistry:
    reg = PackRegistry(packs_dir_with_queries)
    reg.scan_local()
    return reg


@pytest.fixture()
def app_with_queries(registry_with_queries: PackRegistry) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.pack_registry = registry_with_queries
    return app


@pytest.fixture()
def client_with_queries(app_with_queries: FastAPI) -> TestClient:
    return TestClient(app_with_queries)


def test_list_packs_includes_suggested_queries(client_with_queries: TestClient) -> None:
    """GET /api/packs includes suggested_queries field for each pack."""
    resp = client_with_queries.get("/api/packs")
    assert resp.status_code == 200
    packs_data = {p["name"]: p for p in resp.json()["packs"]}

    assert packs_data["python-docs"]["suggestedQueries"] == [
        "What are Python decorators?",
        "How do list comprehensions work?",
    ]
    assert packs_data["fastapi-docs"]["suggestedQueries"] == []


def test_list_packs_suggested_queries_field_present(client: TestClient) -> None:
    """Even packs without suggested_queries.json get an empty list."""
    resp = client.get("/api/packs")
    for pack in resp.json()["packs"]:
        assert "suggestedQueries" in pack
        assert isinstance(pack["suggestedQueries"], list)


def test_get_suggested_queries_endpoint(client_with_queries: TestClient) -> None:
    """GET /api/packs/{id}/suggested-queries returns queries for a specific pack."""
    resp = client_with_queries.get("/api/packs/python-docs/suggested-queries")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pack_id"] == "python-docs"
    assert body["suggested_queries"] == [
        "What are Python decorators?",
        "How do list comprehensions work?",
    ]


def test_get_suggested_queries_empty_for_pack_without(client_with_queries: TestClient) -> None:
    """GET /api/packs/{id}/suggested-queries returns empty list when no file exists."""
    resp = client_with_queries.get("/api/packs/fastapi-docs/suggested-queries")
    assert resp.status_code == 200
    assert resp.json()["suggested_queries"] == []


def test_get_suggested_queries_not_found(client: TestClient) -> None:
    """GET /api/packs/{id}/suggested-queries returns 404 for unknown pack."""
    resp = client.get("/api/packs/nonexistent/suggested-queries")
    assert resp.status_code == 404
