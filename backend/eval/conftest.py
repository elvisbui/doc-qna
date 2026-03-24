"""Pytest configuration and fixtures for the RAG evaluation pipeline."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    """Add --eval-live CLI flag for running evaluations against real providers."""
    parser.addoption(
        "--eval-live",
        action="store_true",
        default=False,
        help="Run evaluation tests against live RAG pipeline (requires API keys)",
    )


@pytest.fixture
def live_eval(request: pytest.FixtureRequest) -> bool:
    """Return True when --eval-live flag is set."""
    return request.config.getoption("--eval-live")


@pytest.fixture
def golden_dataset() -> list[dict[str, Any]]:
    """Load the golden evaluation dataset from JSON."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path) as f:
        return json.load(f)


@pytest.fixture
def mock_rag_pipeline() -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a mock RAG pipeline function for CI testing.

    The mock pipeline returns the expected output and context from the golden
    dataset case directly, simulating a perfect RAG system. This lets us
    verify the evaluation framework wiring without requiring any API keys
    or LLM access.
    """

    def _pipeline(case: dict[str, Any]) -> dict[str, Any]:
        return {
            "actual_output": case["expected_output"],
            "retrieval_context": case["context"],
        }

    return _pipeline
