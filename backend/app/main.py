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
from app.core.constants import APP_VERSION
from app.middleware.auth import APIKeyMiddleware
from app.middleware.errors import register_error_handlers
from app.middleware.logging import CorrelationIDMiddleware, setup_logging
from app.middleware.timing import TimingMiddleware
from app.routers import chat, documents, metrics, packs, plugins
from app.routers import settings as settings_router

settings = get_settings()

# Configure structured JSON logging before anything else logs.
setup_logging(level=settings.LOG_LEVEL)

logger = logging.getLogger(__name__)

# Path to the frontend build output (Vite default)
FRONTEND_DIST = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle.

    On startup, initializes ChromaDB, embedding/LLM provider singletons,
    the embedding cache, the plugin system, and the pack registry. On
    shutdown, closes provider HTTP clients and clears the embedding cache.

    Args:
        app: The FastAPI application instance.

    Yields:
        Control to the application after startup initialization completes.
    """
    # --- Startup ---
    from app.core.constants import COLLECTION_NAME
    from app.core.startup import validate_settings
    from app.providers.embedder import get_embedding_provider
    from app.services.cache import EmbeddingCache
    from app.services.generation import get_llm_provider
    from app.services.vectorstore import get_chroma_client

    # Validate secrets / environment configuration early.
    validate_settings(settings)

    client = get_chroma_client(settings)
    app.state.chroma_client = client
    app.state.chroma_collection = client.get_or_create_collection(name=COLLECTION_NAME)

    # Singleton embedding provider — initialized once, reused across requests.
    app.state.embedder = get_embedding_provider(settings)

    # Singleton LLM provider — avoids creating new httpx clients per request.
    try:
        app.state.llm_provider = get_llm_provider(settings)
    except Exception as exc:
        logger.warning("Could not create LLM provider at startup: %s", exc)
        app.state.llm_provider = None

    # Embedding cache for query embeddings (avoids redundant API calls).
    app.state.embedding_cache = EmbeddingCache(max_size=settings.EMBEDDING_CACHE_SIZE)

    logger.info(
        "Singleton clients initialized: chroma_client, embedder, embedding_cache (size=%d)",
        settings.EMBEDDING_CACHE_SIZE,
    )

    # ── Plugin system ────────────────────────────────────────────────
    from app.plugins.base import PluginBase as _PluginBase
    from app.plugins.loader import PluginRegistry, discover_plugins, load_plugin
    from app.plugins.pipeline import PluginPipeline

    plugins_dir = str(Path(settings.PLUGINS_DIR).resolve())
    registry = PluginRegistry(plugins_dir)
    plugin_instances: list[_PluginBase] = []
    discovered = discover_plugins(plugins_dir)
    for pinfo in discovered:
        try:
            mod = load_plugin(pinfo)
            registry.register(pinfo["name"], mod)
            if hasattr(mod, "register") and registry.plugins[pinfo["name"]].enabled:
                mod.register(app)
            # Collect PluginBase instances for the pipeline.
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name, None)
                if isinstance(obj, type) and obj is not _PluginBase and issubclass(obj, _PluginBase):
                    inst = obj()
                    inst.enabled = registry.plugins[pinfo["name"]].enabled
                    plugin_instances.append(inst)
                    break
            logger.info("Plugin loaded: %s", pinfo["name"])
        except Exception:
            logger.exception("Failed to load plugin %s — skipping", pinfo["name"])
    app.state.plugin_registry = registry
    app.state.plugin_pipeline = PluginPipeline(plugin_instances)

    # Initialise the pack registry once at startup to avoid lazy-init races.
    from app.packs.registry import PackRegistry

    app.state.pack_registry = PackRegistry(settings.PACKS_DIR)

    yield
    # --- Shutdown ---
    # Close async clients held by providers.
    for attr in ("llm_provider", "embedder"):
        provider = getattr(app.state, attr, None)
        client = getattr(provider, "_client", None)
        if client is not None:
            if hasattr(client, "aclose"):
                await client.aclose()
            elif hasattr(client, "close"):
                await client.close()

    # Clear embedding cache on shutdown.
    if hasattr(app.state, "embedding_cache"):
        cache_stats = app.state.embedding_cache.stats
        logger.info("Embedding cache stats at shutdown: %s", cache_stats)
        app.state.embedding_cache.clear()


app = FastAPI(
    title="Doc Q&A API",
    description="RAG-powered document question answering API",
    version=APP_VERSION,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Rate Limiting ─────────────────────────────────────────────────────────────
if settings.RATE_LIMIT_ENABLED:
    from app.middleware.rate_limit import RateLimitMiddleware

    app.add_middleware(RateLimitMiddleware)

# ── API Key Authentication ────────────────────────────────────────────────────
app.add_middleware(APIKeyMiddleware)

# ── Request Timing ───────────────────────────────────────────────────────────
app.add_middleware(TimingMiddleware)

# ── Correlation ID ────────────────────────────────────────────────────────────
app.add_middleware(CorrelationIDMiddleware)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key", "X-Request-ID"],
    expose_headers=["X-Request-ID", "X-Response-Time"],
)

# ── Error handlers ────────────────────────────────────────────────────────────
register_error_handlers(app)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(settings_router.router)
app.include_router(plugins.router)
app.include_router(packs.router)
app.include_router(metrics.router)


# ── Health endpoint ──────────────────────────────────────────────────────────
@app.get(
    "/api/health",
    tags=["health"],
    summary="Check service health",
    description=(
        "Returns overall status (healthy/degraded/unhealthy) and per-dependency "
        "status for ChromaDB, LLM provider, and embedding provider. "
        "Always returns HTTP 200 so monitoring tools can parse the JSON body."
    ),
)
async def health() -> dict:
    """Health check endpoint with dependency status.

    Returns overall status (healthy/degraded/unhealthy) and per-dependency
    status for ChromaDB, LLM provider, and embedding provider.

    Always returns HTTP 200 so monitoring tools can parse the JSON body
    to determine actual health.
    """
    deps: dict[str, dict[str, str]] = {}

    # ── ChromaDB ─────────────────────────────────────────────────────
    try:
        chroma = app.state.chroma_client
        heartbeat = await asyncio.to_thread(chroma.heartbeat)
        deps["chromadb"] = {"status": "up", "detail": f"heartbeat={heartbeat}"}
    except Exception as exc:  # noqa: BLE001
        deps["chromadb"] = {"status": "down", "detail": str(exc)}

    # ── LLM provider ─────────────────────────────────────────────────
    try:
        if settings.LLM_PROVIDER == "ollama":
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                resp.raise_for_status()
            deps["llm"] = {
                "status": "up",
                "detail": f"ollama reachable, model={settings.OLLAMA_MODEL}",
            }
        elif settings.LLM_PROVIDER == "anthropic":
            if settings.ANTHROPIC_API_KEY or settings.ANTHROPIC_AUTH_TOKEN:
                deps["llm"] = {"status": "up", "detail": "anthropic credentials configured"}
            else:
                deps["llm"] = {"status": "down", "detail": "neither ANTHROPIC_API_KEY nor ANTHROPIC_AUTH_TOKEN set"}
        elif settings.LLM_PROVIDER == "openai":
            if settings.OPENAI_API_KEY:
                deps["llm"] = {"status": "up", "detail": "openai API key configured"}
            else:
                deps["llm"] = {"status": "down", "detail": "OPENAI_API_KEY not set"}
        elif settings.LLM_PROVIDER == "cloudflare":
            if settings.CLOUDFLARE_API_TOKEN and settings.CLOUDFLARE_ACCOUNT_ID:
                deps["llm"] = {"status": "up", "detail": "cloudflare credentials configured"}
            else:
                deps["llm"] = {
                    "status": "down",
                    "detail": "CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID not set",
                }
        else:
            deps["llm"] = {
                "status": "down",
                "detail": f"unknown provider: {settings.LLM_PROVIDER}",
            }
    except Exception as exc:  # noqa: BLE001
        deps["llm"] = {"status": "down", "detail": str(exc)}

    # ── Embedder ─────────────────────────────────────────────────────
    try:
        if settings.EMBEDDING_PROVIDER == "ollama":
            async with httpx.AsyncClient(timeout=5.0) as http:
                resp = await http.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
                resp.raise_for_status()
            deps["embedder"] = {
                "status": "up",
                "detail": f"ollama reachable, model={settings.OLLAMA_EMBEDDING_MODEL}",
            }
        elif settings.EMBEDDING_PROVIDER == "openai":
            if settings.OPENAI_API_KEY:
                deps["embedder"] = {
                    "status": "up",
                    "detail": "openai API key configured",
                }
            else:
                deps["embedder"] = {
                    "status": "down",
                    "detail": "OPENAI_API_KEY not set",
                }
        elif settings.EMBEDDING_PROVIDER == "chromadb":
            deps["embedder"] = {
                "status": "up",
                "detail": "chromadb default embedder (local, no API key)",
            }
        elif settings.EMBEDDING_PROVIDER == "cloudflare":
            if settings.CLOUDFLARE_API_TOKEN and settings.CLOUDFLARE_ACCOUNT_ID:
                deps["embedder"] = {
                    "status": "up",
                    "detail": "cloudflare credentials configured",
                }
            else:
                deps["embedder"] = {
                    "status": "down",
                    "detail": "CLOUDFLARE_API_TOKEN or CLOUDFLARE_ACCOUNT_ID not set",
                }
        else:
            deps["embedder"] = {
                "status": "down",
                "detail": f"unknown provider: {settings.EMBEDDING_PROVIDER}",
            }
    except Exception as exc:  # noqa: BLE001
        deps["embedder"] = {"status": "down", "detail": str(exc)}

    # ── Overall status ───────────────────────────────────────────────
    statuses = [d["status"] for d in deps.values()]
    if all(s == "up" for s in statuses):
        overall = "healthy"
    elif all(s == "down" for s in statuses):
        overall = "unhealthy"
    else:
        overall = "degraded"

    return {
        "status": overall,
        "version": APP_VERSION,
        "dependencies": deps,
    }


# ── Static files (serve built frontend) ─────────────────────────────────────
# Only mount if the dist directory exists (avoids crash in dev without a build).
# html=True enables SPA fallback: serves index.html for unmatched paths.
if FRONTEND_DIST.is_dir():
    app.mount(
        "/",
        StaticFiles(directory=str(FRONTEND_DIST), html=True),
        name="frontend",
    )
