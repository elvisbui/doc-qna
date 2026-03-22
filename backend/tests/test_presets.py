"""Tests for the system prompt presets endpoint (GET /api/settings/presets)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings


@pytest.fixture(autouse=True)
def _isolated_settings(tmp_path, monkeypatch):
    """Use a temp directory for UPLOAD_DIR so each test gets a fresh overlay."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()

    test_settings = Settings(
        UPLOAD_DIR=str(upload_dir),
        LLM_PROVIDER="ollama",
        OLLAMA_BASE_URL="http://localhost:11434",
        OLLAMA_MODEL="llama3.2",
        EMBEDDING_PROVIDER="openai",
        EMBEDDING_MODEL="text-embedding-3-small",
        CHUNKING_STRATEGY="fixed",
        RETRIEVAL_STRATEGY="vector",
        LOG_LEVEL="INFO",
        OPENAI_API_KEY="sk-test-key",
        ANTHROPIC_API_KEY=None,
        API_KEYS="",
    )

    monkeypatch.setattr("app.routers.settings.get_settings", lambda: test_settings)
    monkeypatch.setattr("app.core.overlay.get_settings", lambda: test_settings)


@pytest.fixture()
def client():
    """Create a test client that skips the lifespan (no ChromaDB needed)."""
    from app.routers.settings import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestGetPresets:
    """GET /api/settings/presets"""

    def test_returns_all_presets(self, client):
        resp = client.get("/api/settings/presets")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 5

    def test_each_preset_has_required_fields(self, client):
        resp = client.get("/api/settings/presets")
        data = resp.json()
        required_fields = {"id", "name", "description", "systemPrompt"}
        for preset in data:
            assert required_fields.issubset(preset.keys()), (
                f"Preset {preset.get('id', '?')} is missing fields: {required_fields - preset.keys()}"
            )

    def test_each_preset_contains_context_placeholder(self, client):
        resp = client.get("/api/settings/presets")
        data = resp.json()
        for preset in data:
            assert "{context}" in preset["systemPrompt"], (
                f"Preset '{preset['id']}' systemPrompt does not contain the {{{{context}}}} placeholder"
            )

    def test_preset_ids_are_unique(self, client):
        resp = client.get("/api/settings/presets")
        data = resp.json()
        ids = [p["id"] for p in data]
        assert len(ids) == len(set(ids)), "Preset IDs are not unique"

    def test_expected_preset_ids(self, client):
        resp = client.get("/api/settings/presets")
        data = resp.json()
        ids = {p["id"] for p in data}
        expected = {"general", "customer_support", "legal_research", "study_assistant", "technical_docs"}
        assert ids == expected
