"""Retrieval service — vector search for relevant document chunks.

Takes a user query, embeds it, searches ChromaDB for similar chunks,
and returns results as Citation objects. Supports pure vector search
or hybrid retrieval (vector + BM25) with Reciprocal Rank Fusion (RRF).

Pure Python — no FastAPI imports.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING
from uuid import UUID

from app.core.constants import MAX_CHUNKS_PER_QUERY
from app.core.exceptions import RetrievalError
from app.core.models import Citation
from app.providers.embedder import get_embedding_provider
from app.services.bm25 import BM25Index, bm25_search, build_bm25_index
from app.services.vectorstore import get_default_collection, query_similar

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

    from app.config import Settings
    from app.providers.base import EmbeddingProvider
    from app.services.cache import EmbeddingCache

logger = logging.getLogger(__name__)

# Module-level BM25 index cache (lazily built on first hybrid query)
_bm25_index: BM25Index | None = None
_bm25_lock = asyncio.Lock()


# RRF constant (standard value from the original RRF paper)
_RRF_K: int = 60


def invalidate_bm25_cache() -> None:
    """Reset the cached BM25 index so it is rebuilt on the next hybrid query.

    Call this after documents are added or deleted.
    """
    global _bm25_index
    _bm25_index = None


def _reciprocal_rank_fusion(
    ranked_lists: list[list[str]],
    k: int = _RRF_K,
) -> dict[str, float]:
    """Compute Reciprocal Rank Fusion scores across multiple ranked result lists.

    RRF formula: score(d) = sum(1 / (k + rank_i)) for each list where d appears.
    Rank is 1-based (the top result has rank 1).

    Args:
        ranked_lists: A list of ranked ID lists (each ordered best-first).
        k: The RRF constant (default 60).

    Returns:
        A dict mapping document ID to its raw RRF score.
    """
    scores: dict[str, float] = {}
    for ranked_ids in ranked_lists:
        for rank, doc_id in enumerate(ranked_ids, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return scores


def _normalize_rrf_scores(scores: dict[str, float], n_lists: int, k: int = _RRF_K) -> dict[str, float]:
    """Normalize raw RRF scores to the [0, 1] range.

    The theoretical maximum RRF score for a document is:
        n_lists * 1 / (k + 1)   (when the doc is ranked #1 in every list)

    We divide each score by this maximum to get a value in [0, 1].

    Args:
        scores: Raw RRF scores from ``_reciprocal_rank_fusion``.
        n_lists: Number of ranked lists that were fused.
        k: The RRF constant (must match the value used in fusion).

    Returns:
        A dict mapping document ID to its normalized score in [0, 1].
    """
    if not scores or n_lists == 0:
        return scores
    max_possible = n_lists * (1.0 / (k + 1))
    return {doc_id: score / max_possible for doc_id, score in scores.items()}


async def _embed_query(
    query: str,
    embedder: EmbeddingProvider,
    cache: EmbeddingCache | None = None,
) -> list[float]:
    """Embed a query, using the cache when available.

    Args:
        query: The query text to embed.
        embedder: The embedding provider.
        cache: Optional embedding cache for query embeddings.

    Returns:
        The embedding vector for the query.
    """
    if cache is not None:
        cached = cache.get(query)
        if cached is not None:
            logger.debug("Embedding cache hit for query: %.50s...", query)
            return cached

    embedding = await embedder.embed(query)

    if cache is not None and embedding:
        cache.put(query, embedding)

    return embedding


def _build_where_filter(
    document_ids: list[str] | None = None,
    user_id: str | None = None,
) -> dict | None:
    """Build a ChromaDB ``where`` filter combining document and user scoping.

    Args:
        document_ids: Optional list of document IDs to restrict results to.
        user_id: Optional user ID for multi-user isolation.

    Returns:
        A ChromaDB-compatible ``where`` filter dict, or ``None`` when no
        filtering is needed. When both arguments are provided, conditions
        are combined with ``$and``.
    """
    conditions: list[dict] = []
    if document_ids:
        conditions.append({"document_id": {"$in": document_ids}})
    if user_id is not None:
        conditions.append({"user_id": {"$eq": user_id}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


async def _hybrid_retrieve(
    query: str,
    settings: Settings,
    n_results: int,
    collection: Collection,
    document_ids: list[str] | None,
    embedder: EmbeddingProvider | None = None,
    embedding_cache: EmbeddingCache | None = None,
    user_id: str | None = None,
) -> list[Citation]:
    """Run hybrid retrieval: vector search + BM25, fused with RRF.

    Args:
        query: The user's natural language query.
        settings: Application settings.
        n_results: Maximum number of chunks to return.
        collection: The ChromaDB collection.
        document_ids: Optional list of document IDs to scope the search.
        embedder: Optional singleton embedding provider.
        embedding_cache: Optional embedding cache for query embeddings.
        user_id: Optional user namespace for multi-user isolation.

    Returns:
        A list of Citation objects ordered by RRF score (highest first).
    """
    global _bm25_index

    # --- Step 1: Run vector search ---
    if embedder is None:
        embedder = get_embedding_provider(settings)
    query_embedding = await _embed_query(query, embedder, embedding_cache)
    if not query_embedding:
        raise RetrievalError("Failed to generate embedding for query")

    where_filter = _build_where_filter(document_ids, user_id)

    # Fetch more candidates than needed so RRF has enough to fuse
    candidate_count = n_results * 3

    vector_results = await asyncio.to_thread(query_similar, collection, query_embedding, candidate_count, where_filter)

    # --- Step 2: Build / rebuild BM25 index lazily (with lock to prevent races) ---
    async with _bm25_lock:
        if _bm25_index is None or _bm25_index.corpus_size == 0:
            _bm25_index = await asyncio.to_thread(build_bm25_index, collection)
        bm25_idx = _bm25_index  # Capture local ref under lock

    # --- Step 3: Run BM25 search ---
    bm25_results = await asyncio.to_thread(bm25_search, bm25_idx, query, candidate_count)

    # Apply document_ids and user_id filters to BM25 results
    if document_ids:
        doc_id_set = set(document_ids)
        bm25_results = [r for r in bm25_results if r.get("metadata", {}).get("document_id") in doc_id_set]
    if user_id is not None:
        bm25_results = [r for r in bm25_results if r.get("metadata", {}).get("user_id") == user_id]

    # --- Step 4: Build ranked ID lists and compute RRF ---
    vector_ids = [r["id"] for r in vector_results]
    bm25_ids = [r["id"] for r in bm25_results]

    rrf_scores = _reciprocal_rank_fusion([vector_ids, bm25_ids])
    normalized_scores = _normalize_rrf_scores(rrf_scores, n_lists=2)

    # --- Step 5: Build a content lookup from both result sets ---
    content_map: dict[str, dict] = {}
    for r in vector_results:
        content_map[r["id"]] = r
    for r in bm25_results:
        if r["id"] not in content_map:
            content_map[r["id"]] = r

    # --- Step 6: Sort by RRF score and take top-n ---
    sorted_ids = sorted(normalized_scores, key=lambda d: normalized_scores[d], reverse=True)
    top_ids = sorted_ids[:n_results]

    # --- Step 7: Convert to Citation objects ---
    citations: list[Citation] = []
    for doc_id in top_ids:
        entry = content_map.get(doc_id)
        if entry is None:
            continue

        metadata = entry.get("metadata", {})
        doc_id_str = metadata.get("document_id")
        if not doc_id_str:
            logger.warning("Skipping chunk %s: missing document_id metadata", doc_id)
            continue

        try:
            parsed_id = UUID(doc_id_str)
        except ValueError:
            logger.warning("Skipping chunk %s: invalid UUID %r", doc_id, doc_id_str)
            continue

        citation = Citation(
            document_id=parsed_id,
            document_name=metadata.get("document_name", "Unknown"),
            chunk_content=entry.get("content", ""),
            chunk_index=metadata.get("chunk_index", 0),
            relevance_score=normalized_scores.get(doc_id, 0.0),
            page_number=metadata.get("page_number"),
        )
        citations.append(citation)

    return citations


async def retrieve_relevant_chunks(
    query: str,
    settings: Settings,
    n_results: int = MAX_CHUNKS_PER_QUERY,
    collection: Collection | None = None,
    document_ids: list[str] | None = None,
    embedder: EmbeddingProvider | None = None,
    embedding_cache: EmbeddingCache | None = None,
    user_id: str | None = None,
) -> list[Citation]:
    """Retrieve the most relevant document chunks for a user query.

    Embeds the query text using the configured embedder, searches the ChromaDB
    collection for similar chunks, and converts results to Citation objects.

    When ``settings.RETRIEVAL_STRATEGY`` is ``"hybrid"``, both vector search
    and BM25 keyword search are performed and the results are combined using
    Reciprocal Rank Fusion (RRF).

    Args:
        query: The user's natural language query.
        settings: Application settings (API keys, ChromaDB path, etc.).
        n_results: Maximum number of chunks to return.
        collection: Optional ChromaDB collection override.
        document_ids: Optional list of document IDs to scope the search.
        embedder: Optional singleton embedding provider (from app.state).
        embedding_cache: Optional embedding cache for query embeddings.
        user_id: Optional user namespace for multi-user document isolation.

    Returns:
        A list of Citation objects ordered by relevance (most relevant first).

    Raises:
        RetrievalError: If embedding, vector search, or result processing fails.
    """
    if not query.strip():
        return []

    try:
        # Resolve collection
        if collection is None:
            collection = get_default_collection(settings)

        # Resolve embedder (prefer singleton from app.state)
        if embedder is None:
            embedder = get_embedding_provider(settings)

        # Dispatch based on retrieval strategy
        if settings.RETRIEVAL_STRATEGY == "hybrid":
            return await _hybrid_retrieve(
                query,
                settings,
                n_results,
                collection,
                document_ids,
                embedder=embedder,
                embedding_cache=embedding_cache,
                user_id=user_id,
            )

        # --- Default: vector-only retrieval (unchanged logic) ---
        # 1. Embed the query (with cache support)
        query_embedding = await _embed_query(query, embedder, embedding_cache)

        if not query_embedding:
            raise RetrievalError("Failed to generate embedding for query")

        # 2. Build optional where filter for document and user scoping
        where_filter = _build_where_filter(document_ids, user_id)

        # 3. Query for similar chunks (sync — run in thread)
        results = await asyncio.to_thread(query_similar, collection, query_embedding, n_results, where_filter)

        # 4. Convert results to Citation objects
        citations: list[Citation] = []
        for result in results:
            metadata = result.get("metadata", {})
            distance = result.get("distance")

            # Validate required metadata
            doc_id_str = metadata.get("document_id")
            if not doc_id_str:
                logger.warning("Skipping chunk %s: missing document_id metadata", result.get("id"))
                continue

            # Convert L2 distance to relevance score.
            # For normalized embeddings, L2 distance ranges from 0 (identical)
            # to 2 (opposite). Use: score = max(0, 1 - distance/2) to map to 0-1.
            if distance is not None:
                relevance_score = max(0.0, 1.0 - distance / 2.0)
            else:
                relevance_score = 0.0

            try:
                parsed_id = UUID(doc_id_str)
            except ValueError:
                logger.warning("Skipping chunk: invalid UUID %r", doc_id_str)
                continue

            citation = Citation(
                document_id=parsed_id,
                document_name=metadata.get("document_name", "Unknown"),
                chunk_content=result.get("content", ""),
                chunk_index=metadata.get("chunk_index", 0),
                relevance_score=relevance_score,
                page_number=metadata.get("page_number"),
            )
            citations.append(citation)

        return citations

    except RetrievalError:
        raise
    except Exception as exc:
        raise RetrievalError(f"Failed to retrieve relevant chunks: {exc}") from exc
