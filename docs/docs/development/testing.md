---
sidebar_position: 1
---

# Testing

doc-qna has comprehensive test suites for both backend and frontend.

## Running All Tests

```bash
make test
```

Or separately:

```bash
# Backend
cd backend && python3 -m pytest

# Frontend
cd frontend && npx vitest run
```

## Backend Tests (pytest)

Tests live in `backend/tests/`, mirroring the `app/` structure.

```bash
# Run all backend tests
cd backend && python3 -m pytest -v

# Run a specific test file
python3 -m pytest tests/test_ingestion.py

# Run with coverage
python3 -m pytest --cov=app
```

### Test Organization

```
backend/tests/
├── conftest.py              # Shared fixtures
├── test_documents.py        # Document router tests
├── test_chat.py             # Chat router tests
├── test_ingestion.py        # Ingestion service tests
├── test_retrieval.py        # Retrieval service tests
├── test_generation.py       # Generation service tests
├── test_chunking.py         # Chunking strategy tests
├── test_bm25.py             # BM25 search tests
├── test_confidence.py       # Confidence scoring tests
├── test_metrics.py          # Metrics service tests
├── test_summarization.py    # Conversation memory tests
├── test_page_citations.py   # Page-number citation tests
├── test_presets.py          # System prompt preset tests
├── test_plugins.py          # Plugin system tests
└── ...
```

### Async Test Support

Backend tests use `pytest-asyncio` for testing async functions:

```python
import pytest

@pytest.mark.asyncio
async def test_generate_answer():
    result = await generation_service.generate(...)
    assert result is not None
```

## Frontend Tests (Vitest)

```bash
cd frontend && npx vitest run

# Watch mode
npx vitest

# With coverage
npx vitest run --coverage
```

### Test Organization

Tests are colocated with components in `__tests__/` directories:

```
frontend/src/
├── components/chat/__tests__/
│   ├── CitationLink.test.tsx
│   ├── CitationPanel.test.tsx
│   └── parseMessageWithCitations.test.tsx
├── pages/__tests__/
│   ├── SettingsPresets.test.tsx
│   └── MetricsPage.test.tsx
└── lib/__tests__/
    └── ...
```

## Test Environment

Use `backend/.env.example` as reference for required test environment variables. Tests should not require live API keys — mock external providers.
