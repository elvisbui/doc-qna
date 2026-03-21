"""Tests for the Settings API (GET/PUT /api/settings)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
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
    from fastapi import FastAPI

    from app.routers.settings import router

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestGetSettings:
    """GET /api/settings"""

    def test_returns_current_settings(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()

        assert data["llmProvider"] == "ollama"
        assert data["ollamaBaseUrl"] == "http://localhost:11434"
        assert data["ollamaModel"] == "llama3.2"
        assert data["embeddingProvider"] == "openai"
        assert data["embeddingModel"] == "text-embedding-3-small"
        assert data["chunkingStrategy"] == "fixed"
        assert data["retrievalStrategy"] == "vector"
        assert data["logLevel"] == "INFO"
        assert data["hasOpenaiKey"] is True
        assert data["hasAnthropicKey"] is False

    def test_does_not_expose_api_keys(self, client):
        resp = client.get("/api/settings")
        data = resp.json()
        # Should never contain actual key values
        assert "openaiApiKey" not in data
        assert "anthropicApiKey" not in data
        assert "OPENAI_API_KEY" not in data
        assert "ANTHROPIC_API_KEY" not in data

    def test_camel_case_keys(self, client):
        resp = client.get("/api/settings")
        data = resp.json()
        # Verify all keys are camelCase
        for key in data:
            assert "_" not in key, f"Key {key!r} is not camelCase"

    def test_chunk_size_and_overlap_present(self, client):
        resp = client.get("/api/settings")
        data = resp.json()
        assert "chunkSize" in data
        assert "chunkOverlap" in data
        assert isinstance(data["chunkSize"], int)
        assert isinstance(data["chunkOverlap"], int)

    def test_model_params_present_in_response(self, client):
        """GET should return llmTemperature, llmTopP, llmMaxTokens."""
        resp = client.get("/api/settings")
        data = resp.json()
        assert "llmTemperature" in data
        assert "llmTopP" in data
        assert "llmMaxTokens" in data
        assert isinstance(data["llmTemperature"], float)
        assert isinstance(data["llmTopP"], float)
        assert isinstance(data["llmMaxTokens"], int)


class TestPutSettings:
    """PUT /api/settings"""

    def test_update_single_field(self, client):
        resp = client.put("/api/settings", json={"llmProvider": "anthropic"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["llmProvider"] == "anthropic"

    def test_update_multiple_fields(self, client):
        resp = client.put(
            "/api/settings",
            json={
                "llmProvider": "openai",
                "ollamaModel": "mistral",
                "logLevel": "DEBUG",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llmProvider"] == "openai"
        assert data["ollamaModel"] == "mistral"
        assert data["logLevel"] == "DEBUG"

    def test_persists_to_overlay_file(self, client, tmp_path):
        client.put("/api/settings", json={"llmProvider": "anthropic"})

        overlay_path = tmp_path / "settings.json"
        assert overlay_path.exists()
        overlay = json.loads(overlay_path.read_text())
        assert overlay["llm_provider"] == "anthropic"

    def test_overlay_survives_get(self, client):
        client.put("/api/settings", json={"embeddingModel": "text-embedding-ada-002"})

        resp = client.get("/api/settings")
        data = resp.json()
        assert data["embeddingModel"] == "text-embedding-ada-002"

    def test_empty_body_returns_400(self, client):
        resp = client.put("/api/settings", json={})
        assert resp.status_code == 400

    def test_invalid_llm_provider_returns_422(self, client):
        resp = client.put("/api/settings", json={"llmProvider": "invalid"})
        assert resp.status_code == 422

    def test_invalid_embedding_provider_returns_422(self, client):
        resp = client.put("/api/settings", json={"embeddingProvider": "invalid"})
        assert resp.status_code == 422

    def test_invalid_chunking_strategy_returns_422(self, client):
        resp = client.put("/api/settings", json={"chunkingStrategy": "invalid"})
        assert resp.status_code == 422

    def test_invalid_retrieval_strategy_returns_422(self, client):
        resp = client.put("/api/settings", json={"retrievalStrategy": "invalid"})
        assert resp.status_code == 422

    def test_invalid_log_level_returns_422(self, client):
        resp = client.put("/api/settings", json={"logLevel": "TRACE"})
        assert resp.status_code == 422

    def test_chunk_size_too_small_returns_422(self, client):
        resp = client.put("/api/settings", json={"chunkSize": 50})
        assert resp.status_code == 422

    def test_chunk_size_too_large_returns_422(self, client):
        resp = client.put("/api/settings", json={"chunkSize": 20000})
        assert resp.status_code == 422

    def test_chunk_overlap_negative_returns_422(self, client):
        resp = client.put("/api/settings", json={"chunkOverlap": -1})
        assert resp.status_code == 422

    def test_chunk_overlap_ge_chunk_size_returns_422(self, client):
        resp = client.put(
            "/api/settings",
            json={"chunkSize": 500, "chunkOverlap": 500},
        )
        assert resp.status_code == 422

    def test_cannot_set_api_keys(self, client):
        """API keys should not be updatable via this endpoint."""
        resp = client.put("/api/settings", json={"openaiApiKey": "sk-evil"})
        # Should either 422 (unknown field) or ignore the field and 400 (no valid updates)
        assert resp.status_code in (400, 422)

    def test_incremental_updates(self, client):
        """Multiple PUTs should merge, not overwrite."""
        client.put("/api/settings", json={"llmProvider": "anthropic"})
        client.put("/api/settings", json={"logLevel": "DEBUG"})

        resp = client.get("/api/settings")
        data = resp.json()
        assert data["llmProvider"] == "anthropic"
        assert data["logLevel"] == "DEBUG"

    def test_update_chunk_size(self, client):
        resp = client.put("/api/settings", json={"chunkSize": 2000})
        assert resp.status_code == 200
        assert resp.json()["chunkSize"] == 2000

    def test_update_chunk_overlap(self, client):
        resp = client.put("/api/settings", json={"chunkOverlap": 100})
        assert resp.status_code == 200
        assert resp.json()["chunkOverlap"] == 100

    # --- Model parameter tests ---

    def test_update_temperature(self, client):
        resp = client.put("/api/settings", json={"llmTemperature": 0.5})
        assert resp.status_code == 200
        assert resp.json()["llmTemperature"] == 0.5

    def test_update_top_p(self, client):
        resp = client.put("/api/settings", json={"llmTopP": 0.9})
        assert resp.status_code == 200
        assert resp.json()["llmTopP"] == 0.9

    def test_update_max_tokens(self, client):
        resp = client.put("/api/settings", json={"llmMaxTokens": 4096})
        assert resp.status_code == 200
        assert resp.json()["llmMaxTokens"] == 4096

    def test_temperature_too_high_returns_422(self, client):
        resp = client.put("/api/settings", json={"llmTemperature": 2.5})
        assert resp.status_code == 422

    def test_temperature_negative_returns_422(self, client):
        resp = client.put("/api/settings", json={"llmTemperature": -0.1})
        assert resp.status_code == 422

    def test_top_p_too_high_returns_422(self, client):
        resp = client.put("/api/settings", json={"llmTopP": 1.5})
        assert resp.status_code == 422

    def test_top_p_negative_returns_422(self, client):
        resp = client.put("/api/settings", json={"llmTopP": -0.1})
        assert resp.status_code == 422

    def test_max_tokens_too_small_returns_422(self, client):
        resp = client.put("/api/settings", json={"llmMaxTokens": 50})
        assert resp.status_code == 422

    def test_max_tokens_too_large_returns_422(self, client):
        resp = client.put("/api/settings", json={"llmMaxTokens": 99999})
        assert resp.status_code == 422

    def test_temperature_boundary_zero(self, client):
        resp = client.put("/api/settings", json={"llmTemperature": 0.0})
        assert resp.status_code == 200
        assert resp.json()["llmTemperature"] == 0.0

    def test_temperature_boundary_two(self, client):
        resp = client.put("/api/settings", json={"llmTemperature": 2.0})
        assert resp.status_code == 200
        assert resp.json()["llmTemperature"] == 2.0

    def test_model_params_persist_across_requests(self, client):
        """Temperature, top_p, and max_tokens should persist in overlay."""
        client.put("/api/settings", json={"llmTemperature": 0.3})
        client.put("/api/settings", json={"llmTopP": 0.8})
        client.put("/api/settings", json={"llmMaxTokens": 1024})

        resp = client.get("/api/settings")
        data = resp.json()
        assert data["llmTemperature"] == 0.3
        assert data["llmTopP"] == 0.8
        assert data["llmMaxTokens"] == 1024


class TestSystemPrompt:
    """Tests for system_prompt field in settings API."""

    def test_get_returns_system_prompt(self, client):
        """GET should include systemPrompt in the response."""
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "systemPrompt" in data
        assert isinstance(data["systemPrompt"], str)

    def test_update_system_prompt(self, client):
        """PUT should accept and persist a custom system prompt."""
        custom_prompt = "You are a helpful legal assistant."
        resp = client.put("/api/settings", json={"systemPrompt": custom_prompt})
        assert resp.status_code == 200
        assert resp.json()["systemPrompt"] == custom_prompt

    def test_system_prompt_persists_across_requests(self, client):
        """System prompt should survive a round-trip GET after PUT."""
        custom_prompt = "Always respond in bullet points."
        client.put("/api/settings", json={"systemPrompt": custom_prompt})

        resp = client.get("/api/settings")
        assert resp.json()["systemPrompt"] == custom_prompt

    def test_system_prompt_saved_in_overlay(self, client, tmp_path):
        """System prompt should be persisted in the overlay JSON file."""
        custom_prompt = "Be concise."
        client.put("/api/settings", json={"systemPrompt": custom_prompt})

        overlay_path = tmp_path / "settings.json"
        assert overlay_path.exists()
        overlay = json.loads(overlay_path.read_text())
        assert overlay["system_prompt"] == custom_prompt

    def test_system_prompt_max_length_validation(self, client):
        """System prompt exceeding 10000 chars should be rejected."""
        long_prompt = "x" * 10001
        resp = client.put("/api/settings", json={"systemPrompt": long_prompt})
        assert resp.status_code == 422

    def test_system_prompt_empty_string_accepted(self, client):
        """An empty string should be accepted to clear the system prompt."""
        # First set a prompt
        client.put("/api/settings", json={"systemPrompt": "hello"})
        # Then clear it
        resp = client.put("/api/settings", json={"systemPrompt": ""})
        assert resp.status_code == 200
        assert resp.json()["systemPrompt"] == ""

    def test_system_prompt_default_is_empty(self, client):
        """Default system prompt from env should be empty string."""
        resp = client.get("/api/settings")
        assert resp.json()["systemPrompt"] == ""

    def test_system_prompt_used_in_generation_kwargs(self):
        """build_generation_kwargs should include system_prompt from Settings."""
        from app.services.generation import build_generation_kwargs

        settings = Settings(
            UPLOAD_DIR="./uploads",
            SYSTEM_PROMPT="custom prompt",
            API_KEYS="",
        )
        kwargs = build_generation_kwargs(settings)
        assert kwargs["system_prompt"] == "custom prompt"

    def test_system_prompt_falls_back_to_env(self):
        """build_generation_kwargs should use SYSTEM_PROMPT from Settings."""
        from app.services.generation import build_generation_kwargs

        settings = Settings(
            UPLOAD_DIR="./uploads",
            SYSTEM_PROMPT="env default prompt",
            API_KEYS="",
        )
        kwargs = build_generation_kwargs(settings)
        assert kwargs["system_prompt"] == "env default prompt"


class TestEmbeddingModelPicker:
    """Tests for the embedding model picker feature."""

    def test_get_returns_embedding_model(self, client):
        """GET /api/settings should return current embeddingModel."""
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "embeddingModel" in data
        assert data["embeddingModel"] == "text-embedding-3-small"

    def test_get_returns_embedding_provider(self, client):
        """GET /api/settings should return current embeddingProvider."""
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "embeddingProvider" in data
        assert data["embeddingProvider"] == "openai"

    def test_update_embedding_model_openai_small(self, client):
        """Should accept text-embedding-3-small."""
        resp = client.put("/api/settings", json={"embeddingModel": "text-embedding-3-small"})
        assert resp.status_code == 200
        assert resp.json()["embeddingModel"] == "text-embedding-3-small"

    def test_update_embedding_model_openai_large(self, client):
        """Should accept text-embedding-3-large."""
        resp = client.put("/api/settings", json={"embeddingModel": "text-embedding-3-large"})
        assert resp.status_code == 200
        assert resp.json()["embeddingModel"] == "text-embedding-3-large"

    def test_update_embedding_model_openai_ada(self, client):
        """Should accept text-embedding-ada-002."""
        resp = client.put("/api/settings", json={"embeddingModel": "text-embedding-ada-002"})
        assert resp.status_code == 200
        assert resp.json()["embeddingModel"] == "text-embedding-ada-002"

    def test_update_embedding_provider_to_ollama(self, client):
        """Should switch embedding provider to ollama."""
        resp = client.put("/api/settings", json={"embeddingProvider": "ollama"})
        assert resp.status_code == 200
        assert resp.json()["embeddingProvider"] == "ollama"

    def test_update_embedding_provider_to_openai(self, client):
        """Should switch embedding provider to openai."""
        resp = client.put("/api/settings", json={"embeddingProvider": "openai"})
        assert resp.status_code == 200
        assert resp.json()["embeddingProvider"] == "openai"

    def test_update_embedding_model_ollama_model(self, client):
        """Should accept an Ollama embedding model name."""
        resp = client.put("/api/settings", json={"embeddingModel": "nomic-embed-text"})
        assert resp.status_code == 200
        assert resp.json()["embeddingModel"] == "nomic-embed-text"

    def test_update_embedding_provider_and_model_together(self, client):
        """Should update both provider and model in one request."""
        resp = client.put(
            "/api/settings",
            json={
                "embeddingProvider": "ollama",
                "embeddingModel": "mxbai-embed-large",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["embeddingProvider"] == "ollama"
        assert data["embeddingModel"] == "mxbai-embed-large"

    def test_invalid_embedding_provider_rejected(self, client):
        """Should reject invalid embedding provider values."""
        resp = client.put("/api/settings", json={"embeddingProvider": "invalid"})
        assert resp.status_code == 422

    def test_embedding_model_persists_across_gets(self, client):
        """Updated embedding model should persist across subsequent GETs."""
        client.put("/api/settings", json={"embeddingModel": "text-embedding-3-large"})
        resp = client.get("/api/settings")
        assert resp.json()["embeddingModel"] == "text-embedding-3-large"

    def test_embedding_model_persisted_to_overlay(self, client, tmp_path):
        """Embedding model should be written to the overlay file."""
        client.put("/api/settings", json={"embeddingModel": "text-embedding-ada-002"})
        overlay_path = tmp_path / "settings.json"
        assert overlay_path.exists()
        overlay = json.loads(overlay_path.read_text())
        assert overlay["embedding_model"] == "text-embedding-ada-002"

    def test_embedding_provider_persisted_to_overlay(self, client, tmp_path):
        """Embedding provider should be written to the overlay file."""
        client.put("/api/settings", json={"embeddingProvider": "ollama"})
        overlay_path = tmp_path / "settings.json"
        overlay = json.loads(overlay_path.read_text())
        assert overlay["embedding_provider"] == "ollama"

    def test_empty_embedding_model_rejected(self, client):
        """Should reject empty string for embedding model."""
        resp = client.put("/api/settings", json={"embeddingModel": ""})
        assert resp.status_code == 422

    def test_ollama_models_endpoint_returns_models_for_embedding(self, client):
        """GET /api/settings/ollama-models should return models usable for embedding selection."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {"name": "nomic-embed-text", "size": 274_000_000, "modified_at": "2025-01-15T10:30:00Z"},
                {"name": "llama3.2", "size": 2_000_000_000, "modified_at": "2025-01-14T08:00:00Z"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.get("/api/settings/ollama-models")

        assert resp.status_code == 200
        data = resp.json()
        names = [m["name"] for m in data["models"]]
        assert "nomic-embed-text" in names


class TestModelParamsInGeneration:
    """Tests that model params (temperature, top_p, max_tokens) flow into generation kwargs."""

    def test_generation_kwargs_uses_settings_temperature(self):
        from app.services.generation import build_generation_kwargs

        settings = Settings(UPLOAD_DIR="./uploads", API_KEYS="", LLM_TEMPERATURE=0.2)
        kwargs = build_generation_kwargs(settings)
        assert kwargs["temperature"] == 0.2

    def test_generation_kwargs_uses_settings_top_p(self):
        from app.services.generation import build_generation_kwargs

        settings = Settings(UPLOAD_DIR="./uploads", API_KEYS="", LLM_TOP_P=0.9)
        kwargs = build_generation_kwargs(settings)
        assert kwargs["top_p"] == 0.9

    def test_generation_kwargs_uses_settings_max_tokens(self):
        from app.services.generation import build_generation_kwargs

        settings = Settings(UPLOAD_DIR="./uploads", API_KEYS="", LLM_MAX_TOKENS=4096)
        kwargs = build_generation_kwargs(settings)
        assert kwargs["max_tokens"] == 4096

    def test_generation_kwargs_falls_back_to_settings_defaults(self):
        from app.services.generation import build_generation_kwargs

        settings = Settings(
            UPLOAD_DIR="./uploads",
            API_KEYS="",
            LLM_TEMPERATURE=0.5,
            LLM_TOP_P=0.8,
            LLM_MAX_TOKENS=1024,
        )
        with patch("app.core.overlay.load_overlay", return_value={}):
            kwargs = build_generation_kwargs(settings)
        assert kwargs["temperature"] == 0.5
        assert kwargs["top_p"] == 0.8
        assert kwargs["max_tokens"] == 1024


class TestGetOllamaModels:
    """GET /api/settings/ollama-models"""

    def test_returns_models_on_success(self, client):
        """Should return formatted model list when Ollama is reachable."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama3.2",
                    "size": 2_000_000_000,
                    "modified_at": "2025-01-15T10:30:00Z",
                },
                {
                    "name": "mistral",
                    "size": 4_500_000_000,
                    "modified_at": "2025-01-14T08:00:00Z",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.get("/api/settings/ollama-models")

        assert resp.status_code == 200
        data = resp.json()
        assert "models" in data
        assert len(data["models"]) == 2
        assert data["models"][0]["name"] == "llama3.2"
        assert data["models"][0]["size"] == "2.0 GB"
        assert data["models"][0]["modified"] == "2025-01-15T10:30:00Z"
        assert data["models"][1]["name"] == "mistral"
        assert data["models"][1]["size"] == "4.5 GB"

    def test_returns_empty_list_on_connection_error(self, client):
        """Should return empty models list with error when Ollama is unreachable."""
        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.get("/api/settings/ollama-models")

        assert resp.status_code == 200
        data = resp.json()
        assert data["models"] == []
        assert "error" in data
        assert "Could not connect" in data["error"]

    def test_returns_empty_list_on_timeout(self, client):
        """Should return empty models list with error on timeout."""
        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.get("/api/settings/ollama-models")

        assert resp.status_code == 200
        data = resp.json()
        assert data["models"] == []
        assert "error" in data

    def test_returns_empty_list_on_http_error(self, client):
        """Should return empty models list with error on HTTP error status."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_request = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=mock_request, response=mock_response
        )

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.get("/api/settings/ollama-models")

        assert resp.status_code == 200
        data = resp.json()
        assert data["models"] == []
        assert "error" in data
        assert "500" in data["error"]

    def test_formats_size_mb(self, client):
        """Should format sizes in MB correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "tiny-model",
                    "size": 500_000_000,
                    "modified_at": "2025-01-15T10:30:00Z",
                },
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.get("/api/settings/ollama-models")

        data = resp.json()
        assert data["models"][0]["size"] == "500.0 MB"

    def test_no_error_key_on_success(self, client):
        """Should not include error key when fetch succeeds."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.get("/api/settings/ollama-models")

        data = resp.json()
        assert data["models"] == []
        assert "error" not in data


class TestTestConnection:
    """POST /api/settings/test-connection"""

    def test_ollama_success(self, client):
        """Should return ok when Ollama is reachable."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.2"}]}
        mock_response.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.post(
                "/api/settings/test-connection",
                json={"provider": "ollama", "config": {}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "reachable" in data["message"]

    def test_ollama_custom_base_url(self, client):
        """Should use base_url from config if provided."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": []}
        mock_response.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.post(
                "/api/settings/test-connection",
                json={"provider": "ollama", "config": {"base_url": "http://myhost:11434"}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "myhost" in data["message"]

    def test_ollama_connection_error(self, client):
        """Should return error when Ollama is unreachable."""
        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.post(
                "/api/settings/test-connection",
                json={"provider": "ollama", "config": {}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "connect" in data["message"].lower()

    def test_ollama_timeout(self, client):
        """Should return error when Ollama times out."""
        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timed out"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.post(
                "/api/settings/test-connection",
                json={"provider": "ollama", "config": {}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "timed out" in data["message"].lower()

    def test_openai_valid_key_format(self, client):
        """Should attempt to list models with a valid-looking key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            resp = client.post(
                "/api/settings/test-connection",
                json={"provider": "openai", "config": {"api_key": "sk-test123"}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "valid" in data["message"].lower()

    def test_openai_invalid_key_format(self, client):
        """Should reject keys not starting with sk-."""
        resp = client.post(
            "/api/settings/test-connection",
            json={"provider": "openai", "config": {"api_key": "bad-key"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "format" in data["message"].lower()

    def test_openai_no_key(self, client, monkeypatch):
        """Should return error when no OpenAI key is available."""
        # Override settings to have no OpenAI key
        test_settings = Settings(
            UPLOAD_DIR="./uploads",
            OPENAI_API_KEY=None,
            ANTHROPIC_API_KEY=None,
            API_KEYS="",
        )
        monkeypatch.setattr("app.routers.settings.get_settings", lambda: test_settings)
        monkeypatch.setattr("app.core.overlay.get_settings", lambda: test_settings)

        resp = client.post(
            "/api/settings/test-connection",
            json={"provider": "openai", "config": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "no openai" in data["message"].lower()

    def test_openai_uses_env_key_if_no_config_key(self, client):
        """Should fall back to env OPENAI_API_KEY when config has no key."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            # Fixture sets OPENAI_API_KEY="sk-test-key"
            resp = client.post(
                "/api/settings/test-connection",
                json={"provider": "openai", "config": {}},
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    def test_anthropic_valid_key(self, client):
        """Should accept keys starting with sk-ant-."""
        resp = client.post(
            "/api/settings/test-connection",
            json={"provider": "anthropic", "config": {"api_key": "sk-ant-test123"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "valid" in data["message"].lower()

    def test_anthropic_invalid_key_format(self, client):
        """Should reject keys not starting with sk-ant-."""
        resp = client.post(
            "/api/settings/test-connection",
            json={"provider": "anthropic", "config": {"api_key": "sk-wrong-prefix"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "format" in data["message"].lower()

    def test_anthropic_no_key(self, client):
        """Should return error when no Anthropic key is available."""
        # Fixture sets ANTHROPIC_API_KEY=None
        resp = client.post(
            "/api/settings/test-connection",
            json={"provider": "anthropic", "config": {}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "error"
        assert "no anthropic" in data["message"].lower()

    def test_invalid_provider_returns_422(self, client):
        """Should return 422 for unknown provider."""
        resp = client.post(
            "/api/settings/test-connection",
            json={"provider": "invalid", "config": {}},
        )
        assert resp.status_code == 422


class TestApiKeys:
    """POST /api/settings/api-keys and key hint masking."""

    def test_save_openai_key(self, client):
        """Should save an OpenAI API key and reflect it in GET response."""
        resp = client.post(
            "/api/settings/api-keys",
            json={"openaiApiKey": "sk-new-openai-key-1234"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasOpenaiKey"] is True
        # Should not expose the actual key value
        assert "sk-new-openai-key-1234" not in json.dumps(data)

    def test_save_anthropic_key(self, client):
        """Should save an Anthropic API key and reflect it in GET response."""
        resp = client.post(
            "/api/settings/api-keys",
            json={"anthropicApiKey": "sk-ant-my-secret-key9876"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasAnthropicKey"] is True

    def test_save_both_keys(self, client):
        """Should save both keys at once."""
        resp = client.post(
            "/api/settings/api-keys",
            json={
                "openaiApiKey": "sk-openai-test-abcd",
                "anthropicApiKey": "sk-ant-test-efgh",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasOpenaiKey"] is True
        assert data["hasAnthropicKey"] is True

    def test_empty_body_returns_400(self, client):
        """Should reject request with no keys provided."""
        resp = client.post("/api/settings/api-keys", json={})
        assert resp.status_code == 400

    def test_key_persists_across_requests(self, client):
        """Saved keys should be reflected in subsequent GET requests."""
        client.post(
            "/api/settings/api-keys",
            json={"anthropicApiKey": "sk-ant-persist-test1234"},
        )
        resp = client.get("/api/settings")
        data = resp.json()
        assert data["hasAnthropicKey"] is True

    def test_openai_key_hint_masked(self, client):
        """GET should return masked OpenAI key showing only last 4 chars."""
        resp = client.get("/api/settings")
        data = resp.json()
        # Fixture sets OPENAI_API_KEY="sk-test-key"
        assert data["openaiKeyHint"] != ""
        assert data["openaiKeyHint"].endswith("-key")
        # Must not contain the full key
        assert data["openaiKeyHint"] != "sk-test-key"
        # Stars should mask everything except last 4
        assert data["openaiKeyHint"].startswith("*")

    def test_anthropic_key_hint_empty_when_not_set(self, client):
        """GET should return empty hint when Anthropic key is not configured."""
        resp = client.get("/api/settings")
        data = resp.json()
        # Fixture sets ANTHROPIC_API_KEY=None
        assert data["anthropicKeyHint"] == ""

    def test_anthropic_key_hint_masked_after_save(self, client):
        """After saving an Anthropic key, hint should show last 4 chars."""
        client.post(
            "/api/settings/api-keys",
            json={"anthropicApiKey": "sk-ant-secret-WXYZ"},
        )
        resp = client.get("/api/settings")
        data = resp.json()
        assert data["anthropicKeyHint"].endswith("WXYZ")
        assert data["anthropicKeyHint"].startswith("*")
        assert "sk-ant-secret" not in data["anthropicKeyHint"]

    def test_key_hint_short_key_fully_masked(self, client):
        """Keys with 4 or fewer chars should be fully masked."""
        client.post(
            "/api/settings/api-keys",
            json={"openaiApiKey": "abcd"},
        )
        resp = client.get("/api/settings")
        data = resp.json()
        assert data["openaiKeyHint"] == "****"

    def test_key_hint_in_camel_case(self, client):
        """Key hints should be serialized as camelCase."""
        resp = client.get("/api/settings")
        data = resp.json()
        assert "openaiKeyHint" in data
        assert "anthropicKeyHint" in data
        assert "openai_key_hint" not in data
        assert "anthropic_key_hint" not in data


class TestMaskKey:
    """Unit tests for the _mask_key helper."""

    def test_none_returns_empty(self):
        from app.routers.settings import _mask_key

        assert _mask_key(None) == ""

    def test_empty_string_returns_empty(self):
        from app.routers.settings import _mask_key

        assert _mask_key("") == ""

    def test_short_key_returns_stars(self):
        from app.routers.settings import _mask_key

        assert _mask_key("abc") == "****"
        assert _mask_key("abcd") == "****"

    def test_normal_key_shows_last_four(self):
        from app.routers.settings import _mask_key

        result = _mask_key("sk-test-key-ABCD")
        assert result.endswith("ABCD")
        assert result.startswith("*")
        assert len(result) == len("sk-test-key-ABCD")

    def test_five_char_key(self):
        from app.routers.settings import _mask_key

        assert _mask_key("12345") == "*2345"
