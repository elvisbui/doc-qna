"""v1.3 comprehensive tests — settings API, schema validation, CLI smoke tests.

Covers:
- GET/PUT /api/settings (with overlay persistence)
- POST /api/settings/test-connection (all providers)
- GET /api/settings/ollama-models
- POST /api/settings/api-keys
- SettingsUpdateRequest schema validation
- CLI smoke tests: ingest, query, status, config, serve, eval
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from app.cli import app as cli_app
from app.config import Settings
from app.schemas.settings import (
    ApiKeyUpdateRequest,
    ConnectionTestRequest,
    ConnectionTestResponse,
    SettingsResponse,
    SettingsUpdateRequest,
)

cli_runner = CliRunner()


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture()
def isolated_settings(tmp_path, monkeypatch):
    """Create isolated settings with a temp overlay directory."""
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
        OPENAI_API_KEY="sk-test-key-1234",
        ANTHROPIC_API_KEY=None,
        API_KEYS="",
        SYSTEM_PROMPT="You are a helpful assistant.",
        LLM_TEMPERATURE=0.7,
        LLM_TOP_P=1.0,
        LLM_MAX_TOKENS=2048,
    )
    getter = lambda: test_settings
    monkeypatch.setattr("app.routers.settings.get_settings", getter)
    monkeypatch.setattr("app.core.overlay.get_settings", getter)
    return test_settings


@pytest.fixture()
def api_client(isolated_settings):
    """FastAPI test client for settings endpoints."""
    from app.routers.settings import router

    test_app = FastAPI()
    test_app.include_router(router)
    return TestClient(test_app)


# ======================================================================
# Section 1: Settings API — GET /api/settings
# ======================================================================


class TestSettingsGetEndpoint:
    """GET /api/settings — comprehensive tests."""

    def test_returns_200(self, api_client):
        resp = api_client.get("/api/settings")
        assert resp.status_code == 200

    def test_response_contains_all_expected_fields(self, api_client):
        resp = api_client.get("/api/settings")
        data = resp.json()
        expected_fields = [
            "llmProvider",
            "ollamaBaseUrl",
            "ollamaModel",
            "embeddingProvider",
            "embeddingModel",
            "chunkingStrategy",
            "retrievalStrategy",
            "chunkSize",
            "chunkOverlap",
            "logLevel",
            "hasOpenaiKey",
            "hasAnthropicKey",
            "systemPrompt",
            "llmTemperature",
            "llmTopP",
            "llmMaxTokens",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_all_keys_are_camel_case(self, api_client):
        resp = api_client.get("/api/settings")
        data = resp.json()
        for key in data:
            assert "_" not in key, f"Key {key!r} contains underscore — not camelCase"

    def test_does_not_expose_raw_api_keys(self, api_client):
        resp = api_client.get("/api/settings")
        data = resp.json()
        raw = json.dumps(data)
        assert "sk-test-key-1234" not in raw
        assert "openaiApiKey" not in data
        assert "anthropicApiKey" not in data

    def test_has_openai_key_true_when_set(self, api_client):
        resp = api_client.get("/api/settings")
        assert resp.json()["hasOpenaiKey"] is True

    def test_has_anthropic_key_false_when_unset(self, api_client):
        resp = api_client.get("/api/settings")
        assert resp.json()["hasAnthropicKey"] is False

    def test_returns_correct_default_values(self, api_client):
        data = api_client.get("/api/settings").json()
        assert data["llmProvider"] == "ollama"
        assert data["ollamaModel"] == "llama3.2"
        assert data["embeddingProvider"] == "openai"
        assert data["chunkingStrategy"] == "fixed"
        assert data["retrievalStrategy"] == "vector"
        assert data["logLevel"] == "INFO"

    def test_system_prompt_returned(self, api_client):
        data = api_client.get("/api/settings").json()
        assert data["systemPrompt"] == "You are a helpful assistant."

    def test_llm_params_types(self, api_client):
        data = api_client.get("/api/settings").json()
        assert isinstance(data["llmTemperature"], float)
        assert isinstance(data["llmTopP"], float)
        assert isinstance(data["llmMaxTokens"], int)

    def test_key_hints_present(self, api_client):
        data = api_client.get("/api/settings").json()
        # openai key hint should show masked value
        assert "openaiKeyHint" in data
        assert "anthropicKeyHint" in data
        # openai hint should end with last 4 chars of the key
        assert data["openaiKeyHint"].endswith("1234")
        # anthropic hint should be empty since no key set
        assert data["anthropicKeyHint"] == ""


# ======================================================================
# Section 2: Settings API — PUT /api/settings
# ======================================================================


class TestSettingsPutEndpoint:
    """PUT /api/settings — update and validation tests."""

    def test_update_single_field_returns_200(self, api_client):
        resp = api_client.put("/api/settings", json={"llmProvider": "openai"})
        assert resp.status_code == 200
        assert resp.json()["llmProvider"] == "openai"

    def test_update_multiple_fields(self, api_client):
        resp = api_client.put(
            "/api/settings",
            json={"llmProvider": "anthropic", "logLevel": "DEBUG", "ollamaModel": "codellama"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llmProvider"] == "anthropic"
        assert data["logLevel"] == "DEBUG"
        assert data["ollamaModel"] == "codellama"

    def test_empty_body_returns_400(self, api_client):
        resp = api_client.put("/api/settings", json={})
        assert resp.status_code == 400

    def test_overlay_persists_across_get(self, api_client):
        api_client.put("/api/settings", json={"embeddingModel": "custom-model"})
        data = api_client.get("/api/settings").json()
        assert data["embeddingModel"] == "custom-model"

    def test_incremental_updates_merge(self, api_client):
        api_client.put("/api/settings", json={"llmProvider": "openai"})
        api_client.put("/api/settings", json={"logLevel": "ERROR"})
        data = api_client.get("/api/settings").json()
        assert data["llmProvider"] == "openai"
        assert data["logLevel"] == "ERROR"

    def test_chunk_size_update(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkSize": 3000})
        assert resp.status_code == 200
        assert resp.json()["chunkSize"] == 3000

    def test_chunk_overlap_update(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkOverlap": 200})
        assert resp.status_code == 200
        assert resp.json()["chunkOverlap"] == 200

    def test_system_prompt_update(self, api_client):
        resp = api_client.put("/api/settings", json={"systemPrompt": "Be concise."})
        assert resp.status_code == 200
        assert resp.json()["systemPrompt"] == "Be concise."

    def test_temperature_update(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTemperature": 1.5})
        assert resp.status_code == 200
        assert resp.json()["llmTemperature"] == 1.5

    def test_top_p_update(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTopP": 0.5})
        assert resp.status_code == 200
        assert resp.json()["llmTopP"] == 0.5

    def test_max_tokens_update(self, api_client):
        resp = api_client.put("/api/settings", json={"llmMaxTokens": 512})
        assert resp.status_code == 200
        assert resp.json()["llmMaxTokens"] == 512

    # --- Validation errors ---

    def test_invalid_llm_provider_422(self, api_client):
        resp = api_client.put("/api/settings", json={"llmProvider": "gpt5"})
        assert resp.status_code == 422

    def test_invalid_embedding_provider_422(self, api_client):
        resp = api_client.put("/api/settings", json={"embeddingProvider": "azure"})
        assert resp.status_code == 422

    def test_invalid_chunking_strategy_422(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkingStrategy": "random"})
        assert resp.status_code == 422

    def test_invalid_retrieval_strategy_422(self, api_client):
        resp = api_client.put("/api/settings", json={"retrievalStrategy": "brute"})
        assert resp.status_code == 422

    def test_invalid_log_level_422(self, api_client):
        resp = api_client.put("/api/settings", json={"logLevel": "VERBOSE"})
        assert resp.status_code == 422

    def test_chunk_size_below_minimum_422(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkSize": 10})
        assert resp.status_code == 422

    def test_chunk_size_above_maximum_422(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkSize": 50000})
        assert resp.status_code == 422

    def test_chunk_overlap_negative_422(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkOverlap": -5})
        assert resp.status_code == 422

    def test_chunk_overlap_ge_chunk_size_422(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkSize": 500, "chunkOverlap": 500})
        assert resp.status_code == 422

    def test_chunk_overlap_exceeds_chunk_size_422(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkSize": 300, "chunkOverlap": 400})
        assert resp.status_code == 422

    def test_temperature_negative_422(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTemperature": -0.1})
        assert resp.status_code == 422

    def test_temperature_above_max_422(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTemperature": 3.0})
        assert resp.status_code == 422

    def test_top_p_above_max_422(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTopP": 1.5})
        assert resp.status_code == 422

    def test_top_p_negative_422(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTopP": -0.01})
        assert resp.status_code == 422

    def test_max_tokens_too_small_422(self, api_client):
        resp = api_client.put("/api/settings", json={"llmMaxTokens": 10})
        assert resp.status_code == 422

    def test_max_tokens_too_large_422(self, api_client):
        resp = api_client.put("/api/settings", json={"llmMaxTokens": 99999})
        assert resp.status_code == 422

    def test_boundary_temperature_zero(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTemperature": 0.0})
        assert resp.status_code == 200

    def test_boundary_temperature_two(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTemperature": 2.0})
        assert resp.status_code == 200

    def test_boundary_top_p_zero(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTopP": 0.0})
        assert resp.status_code == 200

    def test_boundary_top_p_one(self, api_client):
        resp = api_client.put("/api/settings", json={"llmTopP": 1.0})
        assert resp.status_code == 200

    def test_boundary_chunk_size_min(self, api_client):
        # Set overlap to 0 first so chunk_size=100 is valid
        resp = api_client.put("/api/settings", json={"chunkSize": 100, "chunkOverlap": 0})
        assert resp.status_code == 200

    def test_boundary_chunk_size_max(self, api_client):
        resp = api_client.put("/api/settings", json={"chunkSize": 10000})
        assert resp.status_code == 200

    def test_cannot_set_api_keys_via_put(self, api_client):
        resp = api_client.put("/api/settings", json={"openaiApiKey": "sk-evil"})
        assert resp.status_code in (400, 422)


# ======================================================================
# Section 3: Settings API — POST /api/settings/test-connection
# ======================================================================


class TestSettingsTestConnection:
    """POST /api/settings/test-connection — provider connectivity tests."""

    def test_ollama_success(self, api_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"models": [{"name": "m1"}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.get = AsyncMock(return_value=mock_resp)
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc

            resp = api_client.post(
                "/api/settings/test-connection",
                json={"provider": "ollama", "config": {}},
            )
        assert resp.json()["status"] == "ok"

    def test_ollama_connection_error(self, api_client):
        with patch("app.routers.settings.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc

            resp = api_client.post(
                "/api/settings/test-connection",
                json={"provider": "ollama", "config": {}},
            )
        assert resp.json()["status"] == "error"

    def test_ollama_timeout(self, api_client):
        with patch("app.routers.settings.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc

            resp = api_client.post(
                "/api/settings/test-connection",
                json={"provider": "ollama", "config": {}},
            )
        data = resp.json()
        assert data["status"] == "error"
        assert "timed out" in data["message"].lower()

    def test_openai_valid_key(self, api_client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.get = AsyncMock(return_value=mock_resp)
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc

            resp = api_client.post(
                "/api/settings/test-connection",
                json={"provider": "openai", "config": {"api_key": "sk-valid123"}},
            )
        assert resp.json()["status"] == "ok"

    def test_openai_invalid_key_format(self, api_client):
        resp = api_client.post(
            "/api/settings/test-connection",
            json={"provider": "openai", "config": {"api_key": "bad-key-no-prefix"}},
        )
        data = resp.json()
        assert data["status"] == "error"
        assert "format" in data["message"].lower()

    def test_openai_no_key_available(self, api_client, monkeypatch):
        no_key_settings = Settings(
            UPLOAD_DIR="./uploads",
            OPENAI_API_KEY=None,
            ANTHROPIC_API_KEY=None,
            API_KEYS="",
        )
        monkeypatch.setattr("app.routers.settings.get_settings", lambda: no_key_settings)
        resp = api_client.post(
            "/api/settings/test-connection",
            json={"provider": "openai", "config": {}},
        )
        assert resp.json()["status"] == "error"

    def test_anthropic_valid_key(self, api_client):
        resp = api_client.post(
            "/api/settings/test-connection",
            json={"provider": "anthropic", "config": {"api_key": "sk-ant-valid"}},
        )
        assert resp.json()["status"] == "ok"

    def test_anthropic_invalid_key_format(self, api_client):
        resp = api_client.post(
            "/api/settings/test-connection",
            json={"provider": "anthropic", "config": {"api_key": "wrong-prefix"}},
        )
        assert resp.json()["status"] == "error"

    def test_anthropic_no_key(self, api_client):
        resp = api_client.post(
            "/api/settings/test-connection",
            json={"provider": "anthropic", "config": {}},
        )
        data = resp.json()
        assert data["status"] == "error"
        assert "no anthropic" in data["message"].lower()

    def test_unknown_provider_422(self, api_client):
        resp = api_client.post(
            "/api/settings/test-connection",
            json={"provider": "azure", "config": {}},
        )
        assert resp.status_code == 422


# ======================================================================
# Section 4: Settings API — GET /api/settings/ollama-models
# ======================================================================


class TestSettingsOllamaModels:
    """GET /api/settings/ollama-models — model listing."""

    def test_returns_models_on_success(self, api_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "models": [
                {"name": "llama3.2", "size": 2_000_000_000, "modified_at": "2025-01-01"},
                {"name": "phi3", "size": 800_000_000, "modified_at": "2025-02-01"},
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.get = AsyncMock(return_value=mock_resp)
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc

            resp = api_client.get("/api/settings/ollama-models")

        data = resp.json()
        assert len(data["models"]) == 2
        assert data["models"][0]["name"] == "llama3.2"
        assert "GB" in data["models"][0]["size"]
        assert "MB" in data["models"][1]["size"]
        assert "error" not in data

    def test_connection_error_returns_empty_with_error(self, api_client):
        with patch("app.routers.settings.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc

            resp = api_client.get("/api/settings/ollama-models")

        data = resp.json()
        assert data["models"] == []
        assert "error" in data

    def test_size_formatting_kb(self, api_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"models": [{"name": "tiny", "size": 500_000, "modified_at": ""}]}
        mock_resp.raise_for_status = MagicMock()

        with patch("app.routers.settings.httpx.AsyncClient") as cls:
            mc = AsyncMock()
            mc.get = AsyncMock(return_value=mock_resp)
            mc.__aenter__ = AsyncMock(return_value=mc)
            mc.__aexit__ = AsyncMock(return_value=False)
            cls.return_value = mc

            resp = api_client.get("/api/settings/ollama-models")

        assert "KB" in resp.json()["models"][0]["size"]


# ======================================================================
# Section 5: Settings API — POST /api/settings/api-keys
# ======================================================================


class TestSettingsApiKeys:
    """POST /api/settings/api-keys — key management."""

    def test_set_openai_key(self, api_client):
        resp = api_client.post(
            "/api/settings/api-keys",
            json={"openaiApiKey": "sk-new-key-abcd"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasOpenaiKey"] is True

    def test_set_anthropic_key(self, api_client):
        resp = api_client.post(
            "/api/settings/api-keys",
            json={"anthropicApiKey": "sk-ant-new-key"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasAnthropicKey"] is True

    def test_set_both_keys(self, api_client):
        resp = api_client.post(
            "/api/settings/api-keys",
            json={
                "openaiApiKey": "sk-oai-123",
                "anthropicApiKey": "sk-ant-456",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["hasOpenaiKey"] is True
        assert data["hasAnthropicKey"] is True

    def test_empty_body_returns_400(self, api_client):
        resp = api_client.post("/api/settings/api-keys", json={})
        assert resp.status_code == 400


# ======================================================================
# Section 6: Schema validation — SettingsUpdateRequest
# ======================================================================


class TestSettingsSchemaValidation:
    """Direct pydantic schema validation tests."""

    def test_valid_full_update(self):
        req = SettingsUpdateRequest(
            llm_provider="openai",
            ollama_model="mistral",
            embedding_provider="ollama",
            embedding_model="nomic-embed",
            chunking_strategy="semantic",
            retrieval_strategy="hybrid",
            chunk_size=1000,
            chunk_overlap=100,
            log_level="DEBUG",
            system_prompt="Be brief.",
            llm_temperature=0.5,
            llm_top_p=0.9,
            llm_max_tokens=4096,
        )
        assert req.llm_provider == "openai"
        assert req.chunk_size == 1000

    def test_all_none_is_valid(self):
        req = SettingsUpdateRequest()
        dumped = req.model_dump(exclude_none=True)
        assert dumped == {}

    def test_invalid_provider_raises(self):
        with pytest.raises(Exception):
            SettingsUpdateRequest(llm_provider="gpt5")

    def test_chunk_size_below_min_raises(self):
        with pytest.raises(Exception):
            SettingsUpdateRequest(chunk_size=50)

    def test_chunk_size_above_max_raises(self):
        with pytest.raises(Exception):
            SettingsUpdateRequest(chunk_size=20000)

    def test_chunk_overlap_negative_raises(self):
        with pytest.raises(Exception):
            SettingsUpdateRequest(chunk_overlap=-1)

    def test_temperature_out_of_range_raises(self):
        with pytest.raises(Exception):
            SettingsUpdateRequest(llm_temperature=5.0)

    def test_top_p_out_of_range_raises(self):
        with pytest.raises(Exception):
            SettingsUpdateRequest(llm_top_p=2.0)

    def test_max_tokens_out_of_range_raises(self):
        with pytest.raises(Exception):
            SettingsUpdateRequest(llm_max_tokens=50)

    def test_ollama_model_empty_string_raises(self):
        with pytest.raises(Exception):
            SettingsUpdateRequest(ollama_model="")

    def test_test_connection_request_schema(self):
        req = ConnectionTestRequest(provider="ollama", config={"base_url": "http://x"})
        assert req.provider == "ollama"

    def test_test_connection_request_invalid_provider(self):
        with pytest.raises(Exception):
            ConnectionTestRequest(provider="azure")

    def test_test_connection_response_schema(self):
        resp = ConnectionTestResponse(status="ok", message="connected")
        assert resp.status == "ok"

    def test_api_key_update_request(self):
        req = ApiKeyUpdateRequest(openai_api_key="sk-abc")
        assert req.openai_api_key == "sk-abc"
        assert req.anthropic_api_key is None

    def test_settings_response_camel_case_serialization(self):
        resp = SettingsResponse(
            llm_provider="ollama",
            ollama_base_url="http://localhost:11434",
            ollama_model="llama3.2",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            chunking_strategy="fixed",
            retrieval_strategy="vector",
            chunk_size=1000,
            chunk_overlap=200,
            log_level="INFO",
            has_openai_key=False,
            has_anthropic_key=False,
            has_cloudflare_token=False,
            openai_key_hint="",
            anthropic_key_hint="",
            cloudflare_key_hint="",
            system_prompt="",
            llm_temperature=0.7,
            llm_top_p=1.0,
            llm_max_tokens=2048,
        )
        serialized = resp.model_dump(by_alias=True)
        assert "llmProvider" in serialized
        assert "llm_provider" not in serialized


# ======================================================================
# Section 7: CLI smoke tests
# ======================================================================


class TestCLISmokeIngest:
    """CLI ingest subcommand smoke tests."""

    def test_ingest_help(self):
        result = cli_runner.invoke(cli_app, ["ingest", "--help"])
        assert result.exit_code == 0
        assert "ingest" in result.output.lower() or "Ingest" in result.output

    def test_ingest_missing_path(self, tmp_path):
        missing = tmp_path / "nope.txt"
        result = cli_runner.invoke(cli_app, ["ingest", str(missing)])
        assert result.exit_code == 1

    def test_ingest_unsupported_type(self, tmp_path):
        f = tmp_path / "test.xyz"
        f.write_text("data")
        result = cli_runner.invoke(cli_app, ["ingest", str(f)])
        assert result.exit_code == 1
        assert "Unsupported" in result.output

    @patch("app.services.ingestion.ingest_document", new_callable=AsyncMock)
    def test_ingest_success(self, mock_ingest, tmp_path):
        from uuid import uuid4

        from app.core.models import DocumentChunk

        f = tmp_path / "test.txt"
        f.write_text("Hello world content here.")
        mock_ingest.return_value = [DocumentChunk(document_id=uuid4(), content="chunk", chunk_index=0)]
        result = cli_runner.invoke(cli_app, ["ingest", str(f)])
        assert result.exit_code == 0
        assert "Ingestion complete" in result.output


class TestCLISmokeQuery:
    """CLI query subcommand smoke tests."""

    def test_query_help(self):
        result = cli_runner.invoke(cli_app, ["query", "--help"])
        assert result.exit_code == 0
        assert "question" in result.output.lower()

    def test_query_empty_string(self):
        result = cli_runner.invoke(cli_app, ["query", "   "])
        assert result.exit_code == 1
        assert "empty" in result.output.lower()

    @patch("app.services.retrieval.retrieve_relevant_chunks", new_callable=AsyncMock)
    @patch("app.services.confidence.calculate_confidence", return_value=0.9)
    @patch("app.services.confidence.should_abstain", return_value=False)
    @patch("app.services.generation.get_llm_provider")
    @patch("app.config.get_settings")
    def test_query_success(self, mock_s, mock_prov, mock_abs, mock_conf, mock_ret):
        from uuid import uuid4

        from app.core.models import Citation

        mock_ret.return_value = [
            Citation(
                document_id=uuid4(),
                document_name="doc.pdf",
                chunk_content="content",
                chunk_index=0,
                relevance_score=0.95,
            )
        ]

        async def fake_stream(q, ctx, **kw):
            yield "Test answer"

        mock_prov.return_value.generate_stream = fake_stream
        result = cli_runner.invoke(cli_app, ["query", "What is X?"])
        assert result.exit_code == 0
        assert "Test answer" in result.output


class TestCLISmokeStatus:
    """CLI status subcommand smoke tests."""

    def test_status_help(self):
        result = cli_runner.invoke(cli_app, ["status", "--help"])
        assert result.exit_code == 0

    def test_status_shows_provider_config(self):
        with patch("app.services.vectorstore.get_chroma_client") as mc:
            coll = MagicMock()
            coll.count.return_value = 0
            mc.return_value.get_or_create_collection.return_value = coll
            result = cli_runner.invoke(cli_app, ["status"])
        assert result.exit_code == 0
        assert "Provider Config" in result.output
        assert "LLM Provider" in result.output

    def test_status_shows_chromadb_stats(self):
        with patch("app.services.vectorstore.get_chroma_client") as mc:
            coll = MagicMock()
            coll.count.return_value = 99
            mc.return_value.get_or_create_collection.return_value = coll
            result = cli_runner.invoke(cli_app, ["status"])
        assert "ChromaDB Stats" in result.output
        assert "99" in result.output

    def test_status_handles_chromadb_error(self):
        with patch("app.services.vectorstore.get_chroma_client") as mc:
            mc.side_effect = RuntimeError("connection refused")
            result = cli_runner.invoke(cli_app, ["status"])
        assert result.exit_code == 0
        assert "Error" in result.output or "error" in result.output


class TestCLISmokeConfig:
    """CLI config subcommand smoke tests."""

    @pytest.fixture(autouse=True)
    def _isolate(self, tmp_path, monkeypatch):
        overlay_file = tmp_path / "settings.json"
        monkeypatch.setattr("app.core.overlay.overlay_path", lambda: overlay_file)
        monkeypatch.setattr("app.cli._config_overlay_path", lambda: overlay_file)
        self.overlay_file = overlay_file

    def test_config_help(self):
        result = cli_runner.invoke(cli_app, ["config", "--help"])
        assert result.exit_code == 0

    def test_config_show_all(self):
        result = cli_runner.invoke(cli_app, ["config"])
        assert result.exit_code == 0
        assert "LLM_PROVIDER" in result.output

    def test_config_get(self):
        result = cli_runner.invoke(cli_app, ["config", "get", "LLM_PROVIDER"])
        assert result.exit_code == 0
        # Value depends on environment (.env may override the default)
        assert "LLM_PROVIDER" in result.output

    def test_config_get_case_insensitive(self):
        result = cli_runner.invoke(cli_app, ["config", "get", "llm_provider"])
        assert result.exit_code == 0

    def test_config_get_invalid_key(self):
        result = cli_runner.invoke(cli_app, ["config", "get", "BOGUS"])
        assert result.exit_code == 1
        assert "Unknown key" in result.output

    def test_config_set(self):
        result = cli_runner.invoke(cli_app, ["config", "set", "LLM_PROVIDER", "openai"])
        assert result.exit_code == 0
        assert "Set" in result.output
        data = json.loads(self.overlay_file.read_text())
        assert data["llm_provider"] == "openai"

    def test_config_set_invalid_key(self):
        result = cli_runner.invoke(cli_app, ["config", "set", "NOPE", "val"])
        assert result.exit_code == 1


class TestCLISmokeServe:
    """CLI serve subcommand smoke tests."""

    def test_serve_help(self):
        import re

        result = cli_runner.invoke(cli_app, ["serve", "--help"])
        assert result.exit_code == 0
        output = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        for opt in ("--host", "--port", "--reload", "--workers", "--log-level"):
            assert opt in output

    def test_serve_calls_uvicorn(self):
        with patch("uvicorn.run") as mock_run:
            result = cli_runner.invoke(cli_app, ["serve"])
            assert result.exit_code == 0
            mock_run.assert_called_once()

    def test_serve_custom_options(self):
        with patch("uvicorn.run") as mock_run:
            result = cli_runner.invoke(
                cli_app,
                ["serve", "--host", "127.0.0.1", "--port", "9999", "--workers", "2"],
            )
            assert result.exit_code == 0
            mock_run.assert_called_once_with(
                "app.main:app",
                host="127.0.0.1",
                port=9999,
                reload=False,
                workers=2,
                log_level="info",
            )

    def test_serve_banner(self):
        with patch("uvicorn.run"):
            result = cli_runner.invoke(cli_app, ["serve", "--port", "4444"])
            assert "Doc Q&A Server" in result.output
            assert "4444" in result.output


class TestCLISmokeEval:
    """CLI eval subcommand smoke tests."""

    def test_eval_help(self):
        result = cli_runner.invoke(cli_app, ["eval", "--help"])
        assert result.exit_code == 0
        assert "test" in result.output.lower() or "eval" in result.output.lower()

    def test_eval_missing_file(self):
        result = cli_runner.invoke(cli_app, ["eval", "/nonexistent/test.json"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_eval_invalid_json(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text("not valid json {{{")
        result = cli_runner.invoke(cli_app, ["eval", str(f)])
        assert result.exit_code == 1

    def test_eval_empty_array(self, tmp_path):
        f = tmp_path / "empty.json"
        f.write_text("[]")
        result = cli_runner.invoke(cli_app, ["eval", str(f)])
        assert result.exit_code == 1
        assert "non-empty" in result.output.lower()

    @patch("app.services.retrieval.retrieve_relevant_chunks", new_callable=AsyncMock)
    @patch("app.services.generation.get_llm_provider")
    @patch("app.config.get_settings")
    def test_eval_success(self, mock_s, mock_prov, mock_ret, tmp_path):
        from uuid import uuid4

        from app.core.models import Citation

        mock_ret.return_value = [
            Citation(
                document_id=uuid4(),
                document_name="doc.pdf",
                chunk_content="content about ML",
                chunk_index=0,
                relevance_score=0.9,
            )
        ]

        async def fake_stream(q, ctx, **kw):
            yield "Answer text"

        mock_prov.return_value.generate_stream = fake_stream

        test_file = tmp_path / "cases.json"
        test_file.write_text(json.dumps([{"query": "What is ML?", "expected_answer": "ML is..."}]))

        result = cli_runner.invoke(cli_app, ["eval", str(test_file)])
        assert result.exit_code == 0, f"Unexpected: {result.output}"
        assert "Evaluation Results" in result.output
        assert "Summary" in result.output
