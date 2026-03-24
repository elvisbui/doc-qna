"""Metrics router — exposes query analytics endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Query

from app.services.metrics import get_metrics_summary, get_recent_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["metrics"])


@router.get(
    "/metrics/summary",
    summary="Get aggregated query metrics",
    description="Returns aggregated statistics for the last N days.",
)
async def metrics_summary(
    days: int = Query(default=7, ge=1, le=365, description="Number of days to aggregate"),
) -> dict[str, Any]:
    """Return aggregated query metrics for the specified time window.

    Args:
        days: Number of past days to include in the aggregation
            (default 7, range 1-365).

    Returns:
        A dict containing aggregated stats such as total queries, average
        latency, average relevance score, error rate, and percentile
        latencies.
    """
    return await get_metrics_summary(days=days)


@router.get(
    "/metrics/recent",
    summary="Get recent query metrics",
    description="Returns the most recent raw query metric entries.",
)
async def metrics_recent(
    limit: int = Query(default=100, ge=1, le=1000, description="Max entries to return"),
) -> list[dict[str, Any]]:
    """Return the most recent raw query metric entries.

    Args:
        limit: Maximum number of entries to return (default 100,
            range 1-1000).

    Returns:
        A list of dicts, each representing one recorded query metric
        with fields like ``query_text``, ``latency_ms``,
        ``avg_relevance_score``, and ``error``.
    """
    return await get_recent_metrics(limit=limit)
