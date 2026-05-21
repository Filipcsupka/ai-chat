"""
RAG API — FastAPI entrypoint.

Endpoints:
  GET  /health          liveness probe (quick)
  GET  /ready           readiness probe (checks ChromaDB chunk count)
  POST /chat            main chat endpoint (streaming SSE)
  POST /chat/sync       non-streaming version (for testing)
  POST /ingest          manually re-trigger knowledge base ingestion
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from config import settings
from ingest.loader import ingest_knowledge_base
from rag.embedder import embed_text
from rag.generator import generate, generate_stream
from rag.retriever import count, query

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RAG API — ingesting knowledge base...")
    await ingest_knowledge_base()
    logger.info("Warming up LLM (loading qwen3:8b into VRAM)...")
    try:
        await generate([], "hello")
    except Exception as exc:
        logger.warning("LLM warmup failed (non-fatal): %s", exc)
    logger.info("Ready.")
    yield


app = FastAPI(title="Filip AI Chat API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type"],
    max_age=600,
)


# ── Models ─────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    answer: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/ready")
async def ready():
    """Readiness probe: passes only after knowledge base is ingested."""
    n = await count()
    if n == 0:
        raise HTTPException(status_code=503, detail="Knowledge base not loaded yet")
    return {"status": "ready", "chunks": n}


@app.post("/chat")
async def chat_stream(req: ChatRequest):
    """
    Streaming chat endpoint.

    Returns Server-Sent Events (text/event-stream).
    Each event is a plain text token. The stream ends with a final
    event: 'data: [DONE]\n\n'

    Widget usage:
      const resp = await fetch('/chat', { method: 'POST', body: ... })
      const reader = resp.body.getReader()
      // read tokens and append to message bubble
    """
    question = req.message.strip()

    # Embed query and retrieve relevant context
    query_embedding = await embed_text(question)
    context_chunks = await query(query_embedding, top_k=settings.top_k)

    if not context_chunks:
        logger.warning("No context chunks retrieved for query: %r", question[:80])

    async def event_stream():
        try:
            async for token in generate_stream(context_chunks, question):
                # SSE format: data: <token>\n\n
                # Escape newlines within token to keep SSE framing valid
                safe = token.replace("\n", "\\n")
                yield f"data: {safe}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.error("Stream error: %s", exc)
            yield "data: [ERROR]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@app.post("/chat/sync", response_model=ChatResponse)
async def chat_sync(req: ChatRequest):
    """Non-streaming version. Useful for curl testing and health checks."""
    question = req.message.strip()
    query_embedding = await embed_text(question)
    context_chunks = await query(query_embedding, top_k=settings.top_k)
    answer = await generate(context_chunks, question)
    return ChatResponse(answer=answer)


@app.post("/ingest")
async def manual_ingest():
    """Re-trigger knowledge base ingestion (e.g. after editing knowledge-base/ files)."""
    await ingest_knowledge_base()
    n = await count()
    return {"status": "ingested", "chunks": n}
