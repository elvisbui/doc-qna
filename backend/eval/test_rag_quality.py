"""RAG quality evaluation tests using DeepEval.

Mock mode (default): Uses a mock RAG pipeline and a mock LLM judge to verify
the evaluation framework works correctly without any API keys.

Live mode (--eval-live): Calls the real RAG pipeline endpoints and uses a real
LLM as the evaluation judge.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from deepeval import assert_test
from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    FaithfulnessMetric,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase


class MockEvalLLM(DeepEvalBaseLLM):
    """A mock LLM judge that returns perfect evaluation scores.

    This allows DeepEval metrics to run without any API keys or real LLM
    access. It inspects the prompt to determine which metric is calling it
    and returns the appropriate JSON structure indicating a perfect score.
    """

    def __init__(self) -> None:
        pass

    def load_model(self) -> None:
        return None

    def get_model_name(self) -> str:
        return "mock-eval-llm"

    def generate(self, prompt: str, schema: Any = None) -> Any:
        """Generate a mock response matching the expected schema."""
        if schema is not None:
            return self._generate_from_schema(prompt, schema)
        return "Score: 1.0. The output is perfectly relevant and faithful."

    async def a_generate(self, prompt: str, schema: Any = None) -> Any:
        """Async version of generate."""
        return self.generate(prompt, schema)

    def _generate_from_schema(self, prompt: str, schema: Any) -> Any:
        """Generate a response conforming to the given Pydantic schema."""
        schema_dict = schema.model_json_schema()
        properties = schema_dict.get("properties", {})
        defs = schema_dict.get("$defs", {})
        instance_data = self._build_perfect_response(properties, prompt, defs)
        return schema(**instance_data)

    def _build_perfect_response(
        self,
        properties: dict[str, Any],
        prompt: str,
        schema_defs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build field values that indicate a perfect evaluation score."""
        if schema_defs is None:
            schema_defs = {}

        data: dict[str, Any] = {}
        for field_name, field_info in properties.items():
            field_type = field_info.get("type", "string")

            # Handle arrays first (before substring matching on names)
            if field_type == "array":
                items = field_info.get("items", {})
                if "$ref" in str(items) or items.get("type") == "object":
                    data[field_name] = self._build_array_field(
                        field_name,
                        items,
                        prompt,
                        properties,
                        field_info,
                        schema_defs,
                    )
                else:
                    data[field_name] = []
            elif field_name == "score" or "score" in field_name.lower():
                if field_type == "integer":
                    maximum = field_info.get("maximum", 10)
                    data[field_name] = maximum
                else:
                    data[field_name] = 1.0
            elif field_name == "reason" or "reason" in field_name.lower():
                data[field_name] = (
                    "The output is fully supported by the context and "
                    "directly answers the question with high relevance."
                )
            elif "verdict" in field_name.lower():
                data[field_name] = "yes"
            elif field_type == "number":
                data[field_name] = 1.0
            elif field_type == "integer":
                data[field_name] = 1
            elif field_type == "boolean":
                data[field_name] = True
            else:
                data[field_name] = "Perfect score — fully relevant and faithful."

        return data

    def _build_array_field(
        self,
        field_name: str,
        items: dict,
        prompt: str,
        parent_properties: dict,
        field_info: dict,
        schema_defs: dict | None = None,
    ) -> list:
        """Build array fields, typically verdict lists for metrics."""
        item_props = items.get("properties", {})
        if not item_props:
            # Check $defs for referenced schemas (field-level and top-level)
            defs = {**(schema_defs or {}), **field_info.get("$defs", {})}
            ref = items.get("$ref", "")
            if ref:
                ref_name = ref.split("/")[-1]
                item_props = defs.get(ref_name, {}).get("properties", {})

        if item_props:
            entry: dict[str, Any] = {}
            for k, v in item_props.items():
                t = v.get("type", "string")
                if "verdict" in k.lower():
                    entry[k] = "yes"
                elif "reason" in k.lower():
                    entry[k] = "Fully supported by the context."
                elif t == "number":
                    entry[k] = 1.0
                elif t == "integer":
                    entry[k] = 1
                elif t == "boolean":
                    entry[k] = True
                else:
                    entry[k] = "Relevant and accurate."
            # Return a few entries to simulate multiple claims being verified
            return [entry, entry, entry]

        return []


# ---------------------------------------------------------------------------
# Mock-mode tests (no API keys required)
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_llm() -> MockEvalLLM:
    """Provide a mock LLM judge for evaluation metrics."""
    return MockEvalLLM()


class TestRAGQualityMock:
    """Evaluate RAG quality using mock pipeline and mock LLM judge.

    These tests verify that the evaluation framework is correctly wired
    and produces expected results when given perfect inputs.
    """

    def test_answer_relevancy(
        self,
        golden_dataset: list[dict[str, Any]],
        mock_rag_pipeline: Callable[[dict[str, Any]], dict[str, Any]],
        mock_llm: MockEvalLLM,
    ) -> None:
        """Test that answer relevancy scores meet threshold with perfect data."""
        metric = AnswerRelevancyMetric(threshold=0.5, model=mock_llm)

        for case in golden_dataset:
            result = mock_rag_pipeline(case)
            test_case = LLMTestCase(
                input=case["input"],
                actual_output=result["actual_output"],
                retrieval_context=result["retrieval_context"],
            )
            metric.measure(test_case)
            assert metric.score is not None, "Metric score should not be None"
            assert metric.score >= 0.5, f"Answer relevancy score {metric.score} below threshold for: {case['input']}"

    def test_faithfulness(
        self,
        golden_dataset: list[dict[str, Any]],
        mock_rag_pipeline: Callable[[dict[str, Any]], dict[str, Any]],
        mock_llm: MockEvalLLM,
    ) -> None:
        """Test that faithfulness scores meet threshold with perfect data."""
        metric = FaithfulnessMetric(threshold=0.5, model=mock_llm)

        for case in golden_dataset:
            result = mock_rag_pipeline(case)
            test_case = LLMTestCase(
                input=case["input"],
                actual_output=result["actual_output"],
                retrieval_context=result["retrieval_context"],
            )
            metric.measure(test_case)
            assert metric.score is not None, "Metric score should not be None"
            assert metric.score >= 0.5, f"Faithfulness score {metric.score} below threshold for: {case['input']}"

    def test_contextual_precision(
        self,
        golden_dataset: list[dict[str, Any]],
        mock_rag_pipeline: Callable[[dict[str, Any]], dict[str, Any]],
        mock_llm: MockEvalLLM,
    ) -> None:
        """Test that contextual precision scores meet threshold with perfect data."""
        metric = ContextualPrecisionMetric(threshold=0.5, model=mock_llm)

        for case in golden_dataset:
            result = mock_rag_pipeline(case)
            test_case = LLMTestCase(
                input=case["input"],
                actual_output=result["actual_output"],
                expected_output=case["expected_output"],
                retrieval_context=result["retrieval_context"],
            )
            metric.measure(test_case)
            assert metric.score is not None, "Metric score should not be None"
            assert metric.score >= 0.5, (
                f"Contextual precision score {metric.score} below threshold for: {case['input']}"
            )

    def test_all_metrics_combined(
        self,
        golden_dataset: list[dict[str, Any]],
        mock_rag_pipeline: Callable[[dict[str, Any]], dict[str, Any]],
        mock_llm: MockEvalLLM,
    ) -> None:
        """Run all three metrics on a single case using assert_test."""
        case = golden_dataset[0]
        result = mock_rag_pipeline(case)

        test_case = LLMTestCase(
            input=case["input"],
            actual_output=result["actual_output"],
            expected_output=case["expected_output"],
            retrieval_context=result["retrieval_context"],
        )

        metrics = [
            AnswerRelevancyMetric(threshold=0.5, model=mock_llm),
            FaithfulnessMetric(threshold=0.5, model=mock_llm),
            ContextualPrecisionMetric(threshold=0.5, model=mock_llm),
        ]

        assert_test(test_case, metrics)


# ---------------------------------------------------------------------------
# Live-mode tests (requires --eval-live flag and API keys)
# ---------------------------------------------------------------------------


def _parse_sse_tokens(raw_text: str) -> str:
    """Extract and concatenate token data from an SSE stream response."""
    tokens: list[str] = []
    current_event = ""
    for line in raw_text.splitlines():
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: ") and current_event == "token":
            tokens.append(line[6:])
    return "".join(tokens)


class TestRAGQualityLive:
    """Evaluate RAG quality against the live pipeline.

    These tests are skipped unless --eval-live is passed. They call the
    actual RAG pipeline and use a real LLM judge for evaluation.
    """

    @pytest.fixture(autouse=True)
    def _skip_unless_live(self, live_eval: bool) -> None:
        if not live_eval:
            pytest.skip("Live evaluation tests require --eval-live flag")

    def _query_rag(self, query: str) -> str:
        """Send a query to the live RAG pipeline and parse the SSE response."""
        import httpx

        response = httpx.post(
            "http://localhost:8000/api/chat",
            json={"query": query},
            timeout=60,
        )
        response.raise_for_status()
        return _parse_sse_tokens(response.text)

    def test_live_answer_relevancy(
        self,
        golden_dataset: list[dict[str, Any]],
    ) -> None:
        """Test answer relevancy against the live RAG pipeline."""
        metric = AnswerRelevancyMetric(threshold=0.5)

        for case in golden_dataset[:3]:  # Test a subset in live mode
            actual_output = self._query_rag(case["input"])

            test_case = LLMTestCase(
                input=case["input"],
                actual_output=actual_output,
                retrieval_context=case["context"],
            )
            metric.measure(test_case)
            assert metric.score >= 0.5, (
                f"Live answer relevancy score {metric.score} below threshold for: {case['input']}"
            )

    def test_live_faithfulness(
        self,
        golden_dataset: list[dict[str, Any]],
    ) -> None:
        """Test faithfulness against the live RAG pipeline."""
        metric = FaithfulnessMetric(threshold=0.5)

        for case in golden_dataset[:3]:
            actual_output = self._query_rag(case["input"])

            test_case = LLMTestCase(
                input=case["input"],
                actual_output=actual_output,
                retrieval_context=case["context"],
            )
            metric.measure(test_case)
            assert metric.score >= 0.5, f"Live faithfulness score {metric.score} below threshold for: {case['input']}"

    def test_live_contextual_precision(
        self,
        golden_dataset: list[dict[str, Any]],
    ) -> None:
        """Test contextual precision against the live RAG pipeline."""
        metric = ContextualPrecisionMetric(threshold=0.5)

        for case in golden_dataset[:3]:
            actual_output = self._query_rag(case["input"])

            test_case = LLMTestCase(
                input=case["input"],
                actual_output=actual_output,
                expected_output=case["expected_output"],
                retrieval_context=case["context"],
            )
            metric.measure(test_case)
            assert metric.score >= 0.5, (
                f"Live contextual precision score {metric.score} below threshold for: {case['input']}"
            )
