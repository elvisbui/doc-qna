---
sidebar_position: 2
---

# RAG Evaluation

doc-qna includes a RAG quality evaluation pipeline using [DeepEval](https://github.com/confident-ai/deepeval) to measure answer quality, faithfulness, and retrieval precision.

## Golden Dataset

The evaluation dataset is at `backend/eval/golden_dataset.json` with 10 curated question/expected-answer/expected-context triples:

```json
[
  {
    "question": "What is retrieval-augmented generation?",
    "expected_answer": "RAG is a technique that...",
    "expected_context": "RAG combines retrieval and generation..."
  }
]
```

## Metrics

The evaluation uses three DeepEval metrics:

| Metric | What It Measures |
|--------|-----------------|
| **FaithfulnessMetric** | Is the answer grounded in the retrieved context? (no hallucination) |
| **AnswerRelevancyMetric** | Does the answer actually address the question? |
| **ContextualPrecisionMetric** | Are the retrieved chunks relevant to the question? |

## Running Evaluations

### Mock Mode (CI-safe)

Runs against a mock LLM — no API keys needed:

```bash
cd backend
python3 -m pytest eval/ -v
```

### Live Mode

Runs against your actual RAG pipeline with real providers:

```bash
cd backend
python3 -m pytest eval/ --eval-live -v
```

This sends queries to the running server and evaluates real responses. Requires:
- A running doc-qna instance
- Documents uploaded and indexed
- Valid API keys configured

## Test Structure

```
backend/eval/
├── __init__.py
├── conftest.py               # Fixtures, --eval-live flag
├── test_rag_quality.py       # DeepEval test cases
├── golden_dataset.json       # Curated Q&A triples
└── README.md                 # Detailed evaluation docs
```

## Adding Test Cases

Add new entries to `golden_dataset.json`:

```json
{
  "question": "Your question here",
  "expected_answer": "What the ideal answer should contain",
  "expected_context": "Key text that should appear in retrieved chunks"
}
```

Then re-run the evaluation to see if the pipeline handles the new case well.
