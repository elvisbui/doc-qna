"""Tests for the metrics service."""

import os
import tempfile

import pytest

from app.services.metrics import (
    _initialized_dbs,
    get_metrics_summary,
    get_recent_metrics,
    record_metric,
)


@pytest.fixture()
def tmp_db():
    """Provide a temporary SQLite DB path and clean up afterwards."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # Ensure the path isn't in the initialised cache so the table gets created
    _initialized_dbs.discard(path)
    yield path
    _initialized_dbs.discard(path)
    os.unlink(path)


class TestRecordMetric:
    """Tests for record_metric."""

    @pytest.mark.asyncio
    async def test_writes_to_db(self, tmp_db):
        await record_metric(
            query_text="What is RAG?",
            latency_ms=150.5,
            avg_relevance_score=0.85,
            num_chunks_retrieved=3,
            db_path=tmp_db,
        )

        recent = await get_recent_metrics(limit=10, db_path=tmp_db)
        assert len(recent) == 1
        assert recent[0]["queryText"] == "What is RAG?"
        assert recent[0]["latencyMs"] == pytest.approx(150.5)
        assert recent[0]["avgRelevanceScore"] == pytest.approx(0.85)
        assert recent[0]["numChunksRetrieved"] == 3
        assert recent[0]["error"] is False

    @pytest.mark.asyncio
    async def test_records_error_metric(self, tmp_db):
        await record_metric(
            query_text="bad query",
            latency_ms=50.0,
            error=True,
            error_message="LLM timeout",
            db_path=tmp_db,
        )

        recent = await get_recent_metrics(limit=10, db_path=tmp_db)
        assert len(recent) == 1
        assert recent[0]["error"] is True
        assert recent[0]["errorMessage"] == "LLM timeout"


class TestGetMetricsSummary:
    """Tests for get_metrics_summary."""

    @pytest.mark.asyncio
    async def test_empty_db_returns_zeros(self, tmp_db):
        summary = await get_metrics_summary(days=7, db_path=tmp_db)
        assert summary["totalQueries"] == 0
        assert summary["avgLatencyMs"] == 0.0
        assert summary["p50LatencyMs"] == 0.0
        assert summary["p95LatencyMs"] == 0.0
        assert summary["errorRate"] == 0.0
        assert summary["queriesPerDay"] == []

    @pytest.mark.asyncio
    async def test_aggregates_correctly(self, tmp_db):
        # Insert several metrics
        for i in range(5):
            await record_metric(
                query_text=f"query {i}",
                latency_ms=100.0 + i * 50,
                avg_relevance_score=0.7 + i * 0.05,
                num_chunks_retrieved=3,
                db_path=tmp_db,
            )
        # Insert one error
        await record_metric(
            query_text="error query",
            latency_ms=500.0,
            error=True,
            error_message="fail",
            db_path=tmp_db,
        )

        summary = await get_metrics_summary(days=7, db_path=tmp_db)
        assert summary["totalQueries"] == 6
        assert summary["avgLatencyMs"] > 0
        assert summary["p50LatencyMs"] > 0
        assert summary["p95LatencyMs"] >= summary["p50LatencyMs"]
        # 1 error out of 6 => ~0.1667
        assert summary["errorRate"] == pytest.approx(1 / 6, abs=0.01)
        assert len(summary["queriesPerDay"]) >= 1


class TestGetRecentMetrics:
    """Tests for get_recent_metrics."""

    @pytest.mark.asyncio
    async def test_returns_recent_entries(self, tmp_db):
        for i in range(5):
            await record_metric(
                query_text=f"q{i}",
                latency_ms=float(i * 100),
                db_path=tmp_db,
            )

        recent = await get_recent_metrics(limit=3, db_path=tmp_db)
        assert len(recent) == 3
        # Most recent first (descending id)
        assert recent[0]["queryText"] == "q4"
        assert recent[1]["queryText"] == "q3"
        assert recent[2]["queryText"] == "q2"

    @pytest.mark.asyncio
    async def test_empty_db(self, tmp_db):
        recent = await get_recent_metrics(limit=10, db_path=tmp_db)
        assert recent == []
