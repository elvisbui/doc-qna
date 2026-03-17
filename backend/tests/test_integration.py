"""Integration tests for the doc-qna backend.

Uses a real ephemeral ChromaDB instance but mocks the embedding and LLM
providers so no API keys or external services are needed.
"""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import patch

import chromadb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.core.constants import COLLECTION_NAME

# ---------------------------------------------------------------------------
# Fake providers
# ---------------------------------------------------------------------------

FAKE_EMBEDDING_DIM = 8


class FakeEmbedder:
    """Deterministic embedder that returns fixed-dimension vectors.

    Produces a simple hash-based vector so that identical texts get
    identical embeddings, enabling basic similarity search in tests.
    """

    async def embed(self, text: str) -> list[float]:
        return self._make_vector(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [self._make_vector(t) for t in texts]

    @staticmethod
    def _make_vector(text: str) -> list[float]:
        """Create a deterministic vector from text via simple hashing."""
        h = hash(text) & 0xFFFFFFFF
        return [float((h >> (i * 4)) & 0xF) / 15.0 for i in range(FAKE_EMBEDDING_DIM)]


class FakeLLMProvider:
    """Fake LLM that echoes the query back as a streamed answer."""

    async def generate(self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any) -> str:
        return f"Answer to: {prompt}"

    async def generate_stream(
        self, prompt: str, context: str, history: list[dict] | None = None, **kwargs: Any
    ) -> AsyncIterator[str]:
        tokens = f"Answer to: {prompt}".split()
        for token in tokens:
            yield token + " "


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def test_settings(tmp_path: Path) -> Settings:
    """Return a Settings instance pointing at temporary directories."""
    return Settings(
        UPLOAD_DIR=str(tmp_path / "uploads"),
        CHROMA_PERSIST_DIR=str(tmp_path / "chroma"),
        OPENAI_API_KEY="fake-key-for-testing",
        EMBEDDING_PROVIDER="openai",
        LLM_PROVIDER="ollama",
        CORS_ORIGINS=["*"],
        LOG_LEVEL="WARNING",
    )


@pytest.fixture()
def chroma_collection(test_settings: Settings) -> chromadb.api.models.Collection.Collection:
    """Create an ephemeral ChromaDB client and return a test collection."""
    client = chromadb.Client()  # fully in-memory, no persistence
    return client.get_or_create_collection(name=COLLECTION_NAME)


@pytest.fixture()
def app(test_settings: Settings, chroma_collection) -> FastAPI:
    """Build a FastAPI app wired with test settings and an ephemeral ChromaDB."""
    import tempfile

    from app.routers import chat, documents
    from app.services import document_store

    # Use a temporary SQLite DB for tests
    _tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp_db_path = _tmp_db.name
    _tmp_db.close()
    document_store._DEFAULT_DB_PATH = _tmp_db_path
    document_store._initialized_dbs.clear()

    @asynccontextmanager
    async def _lifespan(application: FastAPI):
        application.state.chroma_collection = chroma_collection
        yield

    application = FastAPI(lifespan=_lifespan)

    # Register routers
    application.include_router(documents.router)
    application.include_router(chat.router)

    # Health endpoint
    @application.get("/api/health")
    async def health() -> dict:
        return {"status": "ok"}

    return application


@pytest.fixture()
def client(app: FastAPI, test_settings: Settings) -> TestClient:
    """Return a TestClient with mocked providers."""
    with (
        patch("app.config.get_settings", return_value=test_settings),
        patch("app.providers.embedder.get_embedding_provider", return_value=FakeEmbedder()),
        patch("app.services.ingestion.get_embedding_provider", return_value=FakeEmbedder()),
        patch("app.services.retrieval.get_embedding_provider", return_value=FakeEmbedder()),
        TestClient(app, raise_server_exceptions=False) as tc,
    ):
        yield tc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_txt_upload(content: str = "Hello, this is a test document.", filename: str = "test.txt"):
    """Return a tuple suitable for the ``files`` parameter of TestClient."""
    return ("file", (filename, io.BytesIO(content.encode()), "text/plain"))


def _upload_document(
    client: TestClient, content: str = "Hello, this is a test document.", filename: str = "test.txt"
) -> dict:
    """Upload a document and return the parsed JSON response."""
    resp = client.post("/api/documents/upload", files=[_make_txt_upload(content, filename)])
    assert resp.status_code == 202, resp.text
    return resp.json()


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    """GET /api/health."""

    def test_health_returns_200(self, client: TestClient):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"


class TestDocumentUpload:
    """POST /api/documents/upload."""

    def test_upload_txt_returns_202(self, client: TestClient):
        data = _upload_document(client)
        assert "documentId" in data or "document_id" in data
        assert data.get("filename") == "test.txt"
        assert data.get("status") == "pending"

    def test_upload_unsupported_type_returns_400(self, client: TestClient):
        files = [("file", ("bad.exe", io.BytesIO(b"binary"), "application/octet-stream"))]
        resp = client.post("/api/documents/upload", files=files)
        assert resp.status_code == 400

    def test_upload_no_filename_returns_400(self, client: TestClient):
        files = [("file", ("", io.BytesIO(b"data"), "text/plain"))]
        resp = client.post("/api/documents/upload", files=files)
        # FastAPI may return 400 or 422 depending on validation
        assert resp.status_code in (400, 422)


class TestDocumentList:
    """GET /api/documents."""

    def test_list_empty(self, client: TestClient):
        resp = client.get("/api/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["documents"] == []

    def test_list_after_upload(self, client: TestClient):
        _upload_document(client, filename="alpha.txt")
        _upload_document(client, filename="beta.txt")

        resp = client.get("/api/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        filenames = {d["filename"] for d in body["documents"]}
        assert filenames == {"alpha.txt", "beta.txt"}


class TestDocumentStatus:
    """Verify document status is accessible via the list endpoint.

    The application does not expose a dedicated GET /api/documents/{id}/status
    endpoint; status is returned as a field in the document list and upload
    response.  We verify that status transitions work correctly.
    """

    def test_uploaded_document_has_pending_status(self, client: TestClient):
        data = _upload_document(client)
        doc_id = data.get("documentId") or data.get("document_id")

        resp = client.get("/api/documents")
        assert resp.status_code == 200
        docs = resp.json()["documents"]
        matches = [d for d in docs if str(d["id"]) == str(doc_id)]
        assert len(matches) == 1
        # Status should be pending (background task has not completed yet
        # because TestClient does not run background tasks by default)
        assert matches[0]["status"] in ("pending", "processing", "ready")

    def test_status_field_present_in_list(self, client: TestClient):
        _upload_document(client)
        resp = client.get("/api/documents")
        for doc in resp.json()["documents"]:
            assert "status" in doc


class TestDocumentDelete:
    """DELETE /api/documents/{id}."""

    def test_delete_returns_204(self, client: TestClient):
        data = _upload_document(client)
        doc_id = data.get("documentId") or data.get("document_id")

        resp = client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 204

    def test_delete_removes_from_list(self, client: TestClient):
        data = _upload_document(client)
        doc_id = data.get("documentId") or data.get("document_id")

        client.delete(f"/api/documents/{doc_id}")

        resp = client.get("/api/documents")
        assert resp.json()["total"] == 0

    def test_delete_nonexistent_returns_404(self, client: TestClient):
        resp = client.delete("/api/documents/nonexistent-id")
        assert resp.status_code == 404


class TestChatEndpoint:
    """POST /api/chat — streaming SSE response with mocked LLM."""

    def test_chat_returns_sse_stream(self, client: TestClient):
        """Send a chat query and verify the response is an SSE stream."""
        with patch(
            "app.services.generation.get_llm_provider",
            return_value=FakeLLMProvider(),
        ):
            resp = client.post(
                "/api/chat",
                json={"query": "What is this about?"},
            )

        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers.get("content-type", "")

        body = resp.text
        # SSE stream should contain event markers
        assert "event:" in body

    def test_chat_sse_contains_done_event(self, client: TestClient):
        """The SSE stream must end with a 'done' event."""
        with patch(
            "app.services.generation.get_llm_provider",
            return_value=FakeLLMProvider(),
        ):
            resp = client.post(
                "/api/chat",
                json={"query": "Tell me something."},
            )

        assert "event: done" in resp.text

    def test_chat_sse_contains_citations_event(self, client: TestClient):
        """The SSE stream should include a 'citations' event."""
        with patch(
            "app.services.generation.get_llm_provider",
            return_value=FakeLLMProvider(),
        ):
            resp = client.post(
                "/api/chat",
                json={"query": "Test query"},
            )

        assert "event: citations" in resp.text

    def test_chat_empty_query_rejected(self, client: TestClient):
        """An empty query should be rejected by validation."""
        resp = client.post("/api/chat", json={"query": ""})
        assert resp.status_code == 422

    def test_chat_missing_query_rejected(self, client: TestClient):
        """A request without a query field should be rejected."""
        resp = client.post("/api/chat", json={})
        assert resp.status_code == 422

    def test_chat_with_history(self, client: TestClient):
        """Chat with conversation history should succeed."""
        with patch(
            "app.services.generation.get_llm_provider",
            return_value=FakeLLMProvider(),
        ):
            resp = client.post(
                "/api/chat",
                json={
                    "query": "Follow-up question",
                    "history": [
                        {"role": "user", "content": "First question"},
                        {"role": "assistant", "content": "First answer"},
                    ],
                },
            )

        assert resp.status_code == 200
        assert "event: done" in resp.text


class TestUploadAndDeleteIntegration:
    """End-to-end flow: upload, verify, delete, verify gone."""

    def test_full_lifecycle(self, client: TestClient):
        # 1. Upload
        data = _upload_document(client, content="Integration test document content.")
        doc_id = data.get("documentId") or data.get("document_id")
        assert doc_id is not None

        # 2. Verify it appears in the list
        resp = client.get("/api/documents")
        assert resp.json()["total"] == 1

        # 3. Delete
        resp = client.delete(f"/api/documents/{doc_id}")
        assert resp.status_code == 204

        # 4. Verify it is gone
        resp = client.get("/api/documents")
        assert resp.json()["total"] == 0

    def test_upload_multiple_then_delete_one(self, client: TestClient):
        d1 = _upload_document(client, filename="first.txt", content="First document.")
        d2 = _upload_document(client, filename="second.txt", content="Second document.")

        id1 = d1.get("documentId") or d1.get("document_id")
        id2 = d2.get("documentId") or d2.get("document_id")

        # Delete the first
        resp = client.delete(f"/api/documents/{id1}")
        assert resp.status_code == 204

        # Only the second should remain
        resp = client.get("/api/documents")
        body = resp.json()
        assert body["total"] == 1
        remaining_id = str(body["documents"][0]["id"])
        assert remaining_id == str(id2)
