"""
Knowledge base ingestion pipeline.

Runs once on API startup (inside the FastAPI lifespan handler).
Flow:
  1. Scan knowledge-base/ directory for *.md files
  2. Chunk each file (paragraph-aware splitter, configurable size + overlap)
  3. Embed each chunk with nomic-embed-text via Ollama
  4. Upsert all chunks into ChromaDB (idempotent — safe to re-run)
  5. Log summary: files processed, chunks stored, total time

On re-deployment the same chunks are upserted again (same IDs → no duplicates).
To add new knowledge: add/edit a .md file, push to GitHub, ArgoCD re-deploys.
"""

import logging
import time
from pathlib import Path

from config import settings
from rag.chunker import chunk_directory
from rag.embedder import embed_batch
from rag.retriever import count, upsert_chunks

logger = logging.getLogger(__name__)


async def ingest_knowledge_base() -> None:
    kb_dir = Path(settings.knowledge_base_dir)
    if not kb_dir.exists():
        logger.error("Knowledge base directory not found: %s", kb_dir)
        return

    md_files = list(kb_dir.glob("*.md"))
    if not md_files:
        logger.warning("No .md files found in %s", kb_dir)
        return

    logger.info("Ingesting knowledge base from %s (%d files)", kb_dir, len(md_files))
    t0 = time.monotonic()

    chunks = chunk_directory(kb_dir, settings.chunk_size, settings.chunk_overlap)
    logger.info("Chunked into %d pieces (size=%d, overlap=%d)", len(chunks), settings.chunk_size, settings.chunk_overlap)

    logger.info("Embedding %d chunks with %s ...", len(chunks), settings.ollama_embed_model)
    embeddings = await embed_batch([c.text for c in chunks])

    await upsert_chunks(chunks, embeddings)
    total = await count()

    elapsed = time.monotonic() - t0
    logger.info(
        "Ingestion complete: %d files → %d chunks → %d total in ChromaDB (%.1fs)",
        len(md_files),
        len(chunks),
        total,
        elapsed,
    )
