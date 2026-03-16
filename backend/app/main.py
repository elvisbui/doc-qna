"""FastAPI application entry point."""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import chat, documents

settings = get_settings()
logger = logging.getLogger(__name__)

FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    from app.core.constants import COLLECTION_NAME
    from app.providers.embedder import get_embedding_provider
    from app.services.cache import EmbeddingCache
    from app.services.generation import get_llm_provider
    from app.services.vectorstore import get_chroma_client

    client = get_chroma_client(settings)
    app.state.chroma_client = client
    app.state.chroma_collection = client.get_or_create_collection(name=COLLECTION_NAME)
    app.state.embedder = get_embedding_provider(settings)

    try:
        app.state.llm_provider = get_llm_provider(settings)
    except Exception as exc:
        logger.warning("Could not create LLM provider at startup: %s", exc)
        app.state.llm_provider = None

    app.state.embedding_cache = EmbeddingCache(max_size=settings.EMBEDDING_CACHE_SIZE)

    logger.info("Startup complete: chroma, embedder, cache initialized")

    yield

    for attr in ("llm_provider", "embedder"):
        provider = getattr(app.state, attr, None)
        client = getattr(provider, "_client", None)
        if client is not None:
            if hasattr(client, "aclose"):
                await client.aclose()
            elif hasattr(client, "close"):
                await client.close()

    if hasattr(app.state, "embedding_cache"):
        app.state.embedding_cache.clear()


app = FastAPI(
    title="Doc Q&A API",
    description="RAG-powered document question answering API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/api/health", tags=["health"])
async def health() -> dict:
    """Health check endpoint."""
    deps: dict[str, dict[str, str]] = {}

    try:
        chroma = app.state.chroma_client
        heartbeat = await asyncio.to_thread(chroma.heartbeat)
        deps["chromadb"] = {"status": "up", "detail": f"heartbeat={heartbeat}"}
    except Exception as exc:
        deps["chromadb"] = {"status": "down", "detail": str(exc)}

    try:
        if settings.LLM_PROVIDER == "ollama":
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                resp.raise_for_status()
            deps["llm"] = {"status": "up", "detail": f"ollama reachable, model={settings.OLLAMA_MODEL}"}
        elif settings.LLM_PROVIDER == "openai":
            if settings.OPENAI_API_KEY:
                deps["llm"] = {"status": "up", "detail": "openai API key configured"}
            else:
                deps["llm"] = {"status": "down", "detail": "OPENAI_API_KEY not set"}
        else:
            deps["llm"] = {"status": "down", "detail": f"unknown provider: {settings.LLM_PROVIDER}"}
    except Exception as exc:
        deps["llm"] = {"status": "down", "detail": str(exc)}

    statuses = [d["status"] for d in deps.values()]
    if all(s == "up" for s in statuses):
        overall = "healthy"
    elif all(s == "down" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return {"status": overall, "version": "0.1.0", "dependencies": deps}


if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
