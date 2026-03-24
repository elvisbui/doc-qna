# RAG Evaluation Pipeline

Automated quality evaluation for the doc-qna RAG pipeline using [DeepEval](https://github.com/confident-ai/deepeval).

## Overview

The evaluation pipeline measures RAG answer quality using three metrics:

| Metric | What it measures | Threshold |
|--------|-----------------|-----------|
| **Answer Relevancy** | How relevant the generated answer is to the input question | 0.5 |
| **Faithfulness** | Whether the answer is grounded in (faithful to) the retrieved context — detects hallucination | 0.5 |
| **Contextual Precision** | Whether the retrieved context chunks that are relevant to the expected answer are ranked higher than irrelevant ones | 0.5 |

Scores range from 0.0 to 1.0. Higher is better. The 0.5 threshold is intentionally moderate to catch regressions without producing false failures.

## Running Tests

### Mock mode (CI — no API keys required)

Uses a mock RAG pipeline (returns perfect answers) and a mock LLM judge to verify the evaluation framework is correctly wired:

```bash
cd backend && python3 -m pytest eval/ -v
```

### Live mode (requires running server + API keys)

Calls the real RAG pipeline at `http://localhost:8000` and uses a real LLM judge (configured via `OPENAI_API_KEY` environment variable, which DeepEval uses by default):

```bash
cd backend && python3 -m pytest eval/ -v --eval-live
```

Make sure the backend server is running before executing live tests.

## Golden Dataset

The evaluation uses a curated set of test cases in `golden_dataset.json`. Each case has:

- **input**: The user question
- **expected_output**: The ideal answer
- **context**: List of context strings that a good retrieval system should find

### Adding new test cases

1. Open `golden_dataset.json`
2. Add a new object to the array:
   ```json
   {
     "input": "Your question here?",
     "expected_output": "The expected ideal answer.",
     "context": [
       "First relevant context chunk.",
       "Second relevant context chunk."
     ]
   }
   ```
3. Run mock tests to verify the new case works: `python3 -m pytest eval/ -v`

## Architecture

```
eval/
├── __init__.py              # Package marker
├── conftest.py              # Pytest fixtures and --eval-live flag
├── golden_dataset.json      # Curated Q&A evaluation cases
├── test_rag_quality.py      # DeepEval metric tests (mock + live)
└── README.md                # This file
```

- **Mock mode** tests use `MockEvalLLM` (a `DeepEvalBaseLLM` subclass) that returns perfect evaluation scores. This proves the framework integration works and can run in CI with zero external dependencies.
- **Live mode** tests call the actual `/api/chat` endpoint and use DeepEval's default LLM judge (OpenAI) to score real responses.
