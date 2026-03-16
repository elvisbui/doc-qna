"""BM25 keyword search service — sparse retrieval for document chunks.

Implements the Okapi BM25 ranking function from scratch (no external library).
Designed to work alongside ChromaDB vector search for hybrid retrieval.

BM25 formula per query term t in document d:
    score(t, d) = IDF(t) * (tf(t,d) * (k1 + 1)) / (tf(t,d) + k1 * (1 - b + b * dl / avgdl))

where:
    tf(t,d)  = term frequency of t in d
    dl       = document length (token count)
    avgdl    = average document length across corpus
    IDF(t)   = log((N - df(t) + 0.5) / (df(t) + 0.5) + 1)
    N        = total number of documents
    df(t)    = number of documents containing term t
    k1, b    = tuning parameters (defaults: 1.5, 0.75)
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from chromadb.api.models.Collection import Collection

# Regex pattern: split on anything that is not a letter or digit
_SPLIT_PATTERN = re.compile(r"[^a-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase text, remove punctuation, and split into tokens.

    Args:
        text: Raw text to tokenize.

    Returns:
        A list of lowercase alphanumeric tokens.
    """
    lowered = text.lower()
    tokens = _SPLIT_PATTERN.split(lowered)
    return [t for t in tokens if t]


@dataclass
class BM25Index:
    """In-memory BM25 index built from a corpus of document chunks.

    Attributes:
        doc_ids: Chunk IDs in corpus order.
        doc_contents: Raw text of each chunk.
        doc_metadatas: Metadata dicts for each chunk.
        tokenized_corpus: Tokenized version of each document.
        doc_lengths: Token count per document.
        avgdl: Average document length across the corpus.
        idf: Mapping from term to its IDF score.
        k1: BM25 term-frequency saturation parameter.
        b: BM25 document-length normalization parameter.
    """

    doc_ids: list[str] = field(default_factory=list)
    doc_contents: list[str] = field(default_factory=list)
    doc_metadatas: list[dict] = field(default_factory=list)
    tokenized_corpus: list[list[str]] = field(default_factory=list)
    doc_lengths: list[int] = field(default_factory=list)
    avgdl: float = 0.0
    idf: dict[str, float] = field(default_factory=dict)
    k1: float = 1.5
    b: float = 0.75

    @property
    def corpus_size(self) -> int:
        """Number of documents in the index."""
        return len(self.doc_ids)


def _compute_idf(tokenized_corpus: list[list[str]], n: int) -> dict[str, float]:
    """Compute IDF for every term in the corpus.

    Uses the standard BM25 IDF formula:
        IDF(t) = log((N - df(t) + 0.5) / (df(t) + 0.5) + 1)

    This variant (with the +1 inside the log) ensures IDF is always
    non-negative, even for terms that appear in more than half the documents.

    Args:
        tokenized_corpus: List of tokenized documents.
        n: Total number of documents.

    Returns:
        A dict mapping each term to its IDF value.
    """
    df: dict[str, int] = {}
    for doc_tokens in tokenized_corpus:
        unique_terms = set(doc_tokens)
        for term in unique_terms:
            df[term] = df.get(term, 0) + 1

    idf: dict[str, float] = {}
    for term, freq in df.items():
        idf[term] = math.log((n - freq + 0.5) / (freq + 0.5) + 1.0)

    return idf


def build_bm25_index(
    collection: Collection,
    k1: float = 1.5,
    b: float = 0.75,
) -> BM25Index:
    """Build a BM25 index from all chunks in a ChromaDB collection.

    Fetches every document from the collection, tokenizes them, and
    pre-computes IDF values and document lengths for fast query-time scoring.

    Args:
        collection: A ChromaDB collection containing document chunks.
        k1: BM25 term-frequency saturation parameter (default 1.5).
        b: BM25 document-length normalization parameter (default 0.75).

    Returns:
        A BM25Index ready for querying via ``bm25_search``.
    """
    count = collection.count()
    if count == 0:
        return BM25Index(k1=k1, b=b)

    # Fetch all documents from ChromaDB
    # ChromaDB's .get() returns all docs when no IDs/filters are specified
    all_docs = collection.get(include=["documents", "metadatas"])

    doc_ids: list[str] = all_docs["ids"] or []
    doc_contents: list[str] = all_docs["documents"] or []
    doc_metadatas: list[dict] = all_docs["metadatas"] or []

    # Tokenize corpus
    tokenized_corpus = [tokenize(content) for content in doc_contents]
    doc_lengths = [len(tokens) for tokens in tokenized_corpus]

    n = len(doc_ids)
    avgdl = sum(doc_lengths) / n if n > 0 else 0.0

    # Compute IDF
    idf = _compute_idf(tokenized_corpus, n)

    return BM25Index(
        doc_ids=doc_ids,
        doc_contents=doc_contents,
        doc_metadatas=doc_metadatas,
        tokenized_corpus=tokenized_corpus,
        doc_lengths=doc_lengths,
        avgdl=avgdl,
        idf=idf,
        k1=k1,
        b=b,
    )


def _score_document(
    query_tokens: list[str],
    doc_tokens: list[str],
    doc_length: int,
    index: BM25Index,
) -> float:
    """Compute the BM25 score for a single document against a query.

    Args:
        query_tokens: Tokenized query terms.
        doc_tokens: Tokenized document terms.
        doc_length: Number of tokens in the document.
        index: The BM25Index (provides IDF, avgdl, k1, b).

    Returns:
        The BM25 relevance score (higher is more relevant).
    """
    score = 0.0
    k1 = index.k1
    b = index.b
    avgdl = index.avgdl or 1.0  # Guard against division by zero

    # Count term frequencies in the document
    tf: dict[str, int] = {}
    for token in doc_tokens:
        tf[token] = tf.get(token, 0) + 1

    for term in query_tokens:
        if term not in index.idf:
            continue
        term_freq = tf.get(term, 0)
        if term_freq == 0:
            continue

        idf = index.idf[term]
        numerator = term_freq * (k1 + 1.0)
        denominator = term_freq + k1 * (1.0 - b + b * doc_length / avgdl)
        score += idf * (numerator / denominator)

    return score


def bm25_search(
    index: BM25Index,
    query: str,
    n_results: int = 5,
) -> list[dict]:
    """Search the BM25 index for chunks matching a keyword query.

    Tokenizes the query, scores every document in the index using BM25,
    and returns the top-n results sorted by score (descending).

    Args:
        index: A pre-built BM25Index.
        query: The user's natural language query.
        n_results: Maximum number of results to return.

    Returns:
        A list of dicts, each containing:
            - ``id``: The chunk ID.
            - ``content``: The chunk text.
            - ``metadata``: The chunk's metadata dict.
            - ``bm25_score``: The BM25 relevance score.
    """
    if index.corpus_size == 0 or not query.strip():
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    # Score all documents
    scores: list[tuple[int, float]] = []
    for i in range(index.corpus_size):
        score = _score_document(
            query_tokens,
            index.tokenized_corpus[i],
            index.doc_lengths[i],
            index,
        )
        if score > 0.0:
            scores.append((i, score))

    # Sort by score descending
    scores.sort(key=lambda x: x[1], reverse=True)

    # Return top-n
    results: list[dict] = []
    for i, bm25_score in scores[:n_results]:
        results.append(
            {
                "id": index.doc_ids[i],
                "content": index.doc_contents[i],
                "metadata": index.doc_metadatas[i],
                "bm25_score": bm25_score,
            }
        )

    return results
