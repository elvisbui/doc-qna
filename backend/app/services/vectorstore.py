"""ChromaDB vector store integration for document chunk storage and retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import chromadb
    from chromadb.api.models.Collection import Collection

    from app.config import Settings
    from app.core.models import DocumentChunk


def get_chroma_client(settings: Settings) -> chromadb.ClientAPI:
    """Create a ChromaDB client based on the configured mode.

    Args:
        settings: Application settings containing CHROMA_MODE and connection details.

    Returns:
        A ChromaDB client (PersistentClient for embedded, HttpClient for client mode).
    """
    import chromadb

    if settings.CHROMA_MODE == "client":
        return chromadb.HttpClient(host=settings.CHROMA_HOST, port=settings.CHROMA_PORT)
    return chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)


def get_default_collection(settings: Settings) -> Collection:
    """Return a ChromaDB collection, creating the client if needed.

    This is a fallback for when no collection is passed from app.state
    (e.g., during testing or CLI usage).

    Args:
        settings: Application settings containing ChromaDB configuration.

    Returns:
        A ChromaDB ``Collection`` instance (created if it does not exist).
    """
    from app.core.constants import COLLECTION_NAME

    client = get_chroma_client(settings)
    return client.get_or_create_collection(name=COLLECTION_NAME)


def add_chunks(
    collection: Collection,
    chunks: list[DocumentChunk],
    embeddings: list[list[float]],
) -> None:
    """Add document chunks with their embeddings to the collection.

    Each chunk is stored with its content as the document, its embedding,
    and metadata containing the document_id and chunk_index.

    Args:
        collection: The ChromaDB collection to add to.
        chunks: List of DocumentChunk instances to store.
        embeddings: Corresponding embedding vectors for each chunk.
    """
    ids = [str(chunk.id) for chunk in chunks]
    documents = [chunk.content for chunk in chunks]
    metadatas = [
        {
            **chunk.metadata,
            "document_id": str(chunk.document_id),
            "chunk_index": chunk.chunk_index,
        }
        for chunk in chunks
    ]

    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def query_similar(
    collection: Collection,
    query_embedding: list[float],
    n_results: int,
    where: dict | None = None,
) -> list[dict]:
    """Query for similar chunks using a query embedding.

    Args:
        collection: The ChromaDB collection to query.
        query_embedding: The embedding vector for the query.
        n_results: Maximum number of results to return.

        where: Optional ChromaDB ``where`` filter dict for scoping results.

    Returns:
        A list of dicts, each containing:
          - ``id``: The chunk ID string.
          - ``content``: The chunk text.
          - ``metadata``: A dict of chunk metadata (``document_id``,
            ``chunk_index``, etc.).
          - ``distance``: The L2 distance from the query embedding, or
            ``None`` if unavailable.
    """
    # Clamp n_results to collection size to avoid ChromaDB error
    count = collection.count()
    if count == 0:
        return []
    effective_n = min(n_results, count)

    query_kwargs: dict = {
        "query_embeddings": [query_embedding],
        "n_results": effective_n,
    }
    if where is not None:
        query_kwargs["where"] = where

    results = collection.query(**query_kwargs)

    output: list[dict] = []
    if not results["ids"] or not results["ids"][0]:
        return output

    for i, chunk_id in enumerate(results["ids"][0]):
        entry: dict = {
            "id": chunk_id,
            "content": results["documents"][0][i] if results["documents"] else "",
            "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
            "distance": results["distances"][0][i] if results["distances"] else None,
        }
        output.append(entry)

    return output


def delete_by_document_id(collection: Collection, document_id: str) -> None:
    """Delete all chunks for a given document from the collection.

    Args:
        collection: The ChromaDB collection to delete from.
        document_id: The document ID whose chunks should be removed.
    """
    collection.delete(
        where={"document_id": document_id},
    )
