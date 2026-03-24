"""Metrics collection service — records and aggregates query analytics.

Uses SQLite (via aiosqlite) for lightweight, persistent metrics storage.
"""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

# Default DB path — sits alongside the backend package.
_DEFAULT_DB_PATH = str(Path(__file__).resolve().parent.parent.parent / "metrics.db")

SECONDS_PER_DAY = 86_400

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS query_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    query_text TEXT NOT NULL,
    latency_ms REAL NOT NULL,
    avg_relevance_score REAL NOT NULL DEFAULT 0.0,
    num_chunks_retrieved INTEGER NOT NULL DEFAULT 0,
    token_count INTEGER,
    error INTEGER NOT NULL DEFAULT 0,
    error_message TEXT
)
"""

_initialized_dbs: set[str] = set()


@asynccontextmanager
async def _get_db(db_path: str | None = None) -> AsyncIterator[aiosqlite.Connection]:
    """Open a connection, ensure the table exists, and close on exit.

    Args:
        db_path: Optional path to the SQLite database file. Defaults to
            ``_DEFAULT_DB_PATH`` when ``None``.

    Yields:
        An open ``aiosqlite.Connection`` with the ``query_metrics`` table
        guaranteed to exist.
    """
    path = db_path or _DEFAULT_DB_PATH
    async with aiosqlite.connect(path) as db:
        if path not in _initialized_dbs:
            await db.execute(_CREATE_TABLE_SQL)
            await db.commit()
            _initialized_dbs.add(path)
        yield db


async def record_metric(
    query_text: str,
    latency_ms: float,
    avg_relevance_score: float = 0.0,
    num_chunks_retrieved: int = 0,
    token_count: int | None = None,
    error: bool = False,
    error_message: str | None = None,
    db_path: str | None = None,
) -> None:
    """Insert a single query metric row.

    Args:
        query_text: The user query that was processed.
        latency_ms: End-to-end query latency in milliseconds.
        avg_relevance_score: Mean relevance score of retrieved chunks.
        num_chunks_retrieved: Number of chunks returned by retrieval.
        token_count: Optional total token count for the LLM call.
        error: Whether the query resulted in an error.
        error_message: Optional error description when ``error`` is ``True``.
        db_path: Optional path to the SQLite database file.
    """
    async with _get_db(db_path) as db:
        await db.execute(
            """
            INSERT INTO query_metrics
                (timestamp, query_text, latency_ms, avg_relevance_score,
                 num_chunks_retrieved, token_count, error, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                time.time(),
                query_text,
                latency_ms,
                avg_relevance_score,
                num_chunks_retrieved,
                token_count,
                1 if error else 0,
                error_message,
            ),
        )
        await db.commit()


async def get_metrics_summary(days: int = 7, db_path: str | None = None) -> dict[str, Any]:
    """Return aggregated stats for the last *days* days.

    Args:
        days: Number of days to look back for aggregation.
        db_path: Optional path to the SQLite database file.

    Returns:
        A dict with keys ``totalQueries``, ``avgLatencyMs``,
        ``p50LatencyMs``, ``p95LatencyMs``, ``avgRelevanceScore``,
        ``errorRate``, and ``queriesPerDay`` (a list of date/count dicts).
    """
    async with _get_db(db_path) as db:
        cutoff = time.time() - days * SECONDS_PER_DAY

        # Basic aggregates
        cursor = await db.execute(
            """
            SELECT
                COUNT(*) AS total_queries,
                COALESCE(AVG(latency_ms), 0) AS avg_latency_ms,
                COALESCE(AVG(avg_relevance_score), 0) AS avg_relevance_score,
                COALESCE(SUM(error) * 1.0 / NULLIF(COUNT(*), 0), 0) AS error_rate
            FROM query_metrics
            WHERE timestamp >= ?
            """,
            (cutoff,),
        )
        row = await cursor.fetchone()
        total_queries = row[0]
        avg_latency_ms = row[1]
        avg_relevance_score = row[2]
        error_rate = row[3]

        # Percentiles — fetch all latencies and compute in Python
        cursor = await db.execute(
            "SELECT latency_ms FROM query_metrics WHERE timestamp >= ? ORDER BY latency_ms",
            (cutoff,),
        )
        latencies = [r[0] for r in await cursor.fetchall()]

        if latencies:
            p50_idx = max(0, int(len(latencies) * 0.5) - 1)
            p95_idx = max(0, int(len(latencies) * 0.95) - 1)
            p50_latency_ms = latencies[p50_idx]
            p95_latency_ms = latencies[p95_idx]
        else:
            p50_latency_ms = 0.0
            p95_latency_ms = 0.0

        # Queries per day breakdown
        cursor = await db.execute(
            """
            SELECT date(timestamp, 'unixepoch') AS day, COUNT(*) AS cnt
            FROM query_metrics
            WHERE timestamp >= ?
            GROUP BY day
            ORDER BY day
            """,
            (cutoff,),
        )
        queries_per_day = [{"date": r[0], "count": r[1]} for r in await cursor.fetchall()]

        return {
            "totalQueries": total_queries,
            "avgLatencyMs": round(avg_latency_ms, 2),
            "p50LatencyMs": round(p50_latency_ms, 2),
            "p95LatencyMs": round(p95_latency_ms, 2),
            "avgRelevanceScore": round(avg_relevance_score, 4),
            "errorRate": round(error_rate, 4),
            "queriesPerDay": queries_per_day,
        }


async def get_recent_metrics(limit: int = 100, db_path: str | None = None) -> list[dict[str, Any]]:
    """Return the most recent metric rows.

    Args:
        limit: Maximum number of rows to return. Defaults to 100.
        db_path: Optional path to the SQLite database file.

    Returns:
        A list of dicts, each with keys ``id``, ``timestamp``,
        ``queryText``, ``latencyMs``, ``avgRelevanceScore``,
        ``numChunksRetrieved``, ``tokenCount``, ``error``, and
        ``errorMessage``, ordered by most recent first.
    """
    async with _get_db(db_path) as db:
        cursor = await db.execute(
            """
            SELECT id, timestamp, query_text, latency_ms, avg_relevance_score,
                   num_chunks_retrieved, token_count, error, error_message
            FROM query_metrics
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "queryText": r[2],
                "latencyMs": r[3],
                "avgRelevanceScore": r[4],
                "numChunksRetrieved": r[5],
                "tokenCount": r[6],
                "error": bool(r[7]),
                "errorMessage": r[8],
            }
            for r in rows
        ]
