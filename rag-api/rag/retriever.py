"""
ChromaDB retrieval layer.

ChromaDB runs as a k8s pod on the GPU node (ai-chat namespace).
It persists vector data to a PVC so chunks survive pod restarts.

Collection layout:
  - id:        "{source}_{index}"   e.g. "profile_0", "experience_3"
  - document:  raw chunk text
  - embedding: nomic-embed-text vector (768 dims)
  - metadata:  {"source": "<filename stem>", "index": <int>}

Query returns the top-k chunks by cosine similarity to the query embedding.
"""

import chromadb
from chromadb.config import Settings as ChromaSettings

from config import settings
from rag.chunker import Chunk


_client = None
_collection = None


async def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = await chromadb.AsyncHttpClient(
            host=settings.chromadb_host,
            port=settings.chromadb_port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        _collection = await _client.get_or_create_collection(
            name=settings.chromadb_collection,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


async def upsert_chunks(chunks: list[Chunk], embeddings: list[list[float]]) -> None:
    """
    Insert or replace all chunks in ChromaDB.

    Called on startup after the knowledge base is loaded and embedded.
    Uses upsert so re-deploying with the same content is idempotent.
    """
    collection = await _get_collection()
    await collection.upsert(
        ids=[f"{c.source}_{c.index}" for c in chunks],
        documents=[c.text for c in chunks],
        embeddings=embeddings,
        metadatas=[{"source": c.source, "index": c.index} for c in chunks],
    )


async def query(embedding: list[float], top_k: int | None = None) -> list[str]:
    """
    Return the top-k most relevant text chunks for the given query embedding.

    The returned list is ordered by relevance (highest similarity first).
    Each item is raw chunk text, ready to be injected into the LLM prompt.
    """
    k = top_k or settings.top_k
    collection = await _get_collection()
    results = await collection.query(
        query_embeddings=[embedding],
        n_results=k,
        include=["documents"],
    )
    docs: list[str] = results["documents"][0] if results["documents"] else []
    return docs


async def count() -> int:
    """Return total number of chunks stored (useful for health checks and logs)."""
    collection = await _get_collection()
    return await collection.count()
