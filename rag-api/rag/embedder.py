"""
Embedding via Ollama's /api/embeddings endpoint.

Ollama runs on the GPU node host (OLLAMA_HOST=0.0.0.0) and is exposed to
k8s pods via a ClusterIP Service backed by a manual Endpoints object pointing
to the node's Tailscale IP (100.86.152.16:11434).

The embedding model (nomic-embed-text) is tiny (~274MB) and stays loaded
between calls because it is much smaller than the chat model. Ollama manages
VRAM automatically — if the chat model is active, the embed model loads on
CPU; if both idle, both can fit in VRAM simultaneously.
"""

import httpx

from config import settings


async def embed_text(text: str) -> list[float]:
    """Return a single embedding vector for the given text."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{settings.ollama_url}/api/embeddings",
            json={"model": settings.ollama_embed_model, "prompt": text},
        )
        response.raise_for_status()
        return response.json()["embedding"]


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Return embedding vectors for a list of texts (sequential, Ollama has no batch endpoint)."""
    results: list[list[float]] = []
    for text in texts:
        results.append(await embed_text(text))
    return results
