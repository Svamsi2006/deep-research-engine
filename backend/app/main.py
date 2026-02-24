"""FastAPI application entry point for Engineering Oracle."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import init_db
from app.middleware import ErrorHandlingMiddleware
from app.routes.chat import router as chat_router
from app.routes.reports import router as reports_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-28s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown hooks
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    settings = get_settings()

    # 1. Database
    logger.info("Initializing SQLite database...")
    await init_db(settings.database_url)

    # 2. ChromaDB + Embeddings (lazy — initialized on first use)
    logger.info("Evaluator will initialize on first use (ChromaDB + embeddings)")

    logger.info("=" * 60)
    logger.info("  Engineering Oracle — Backend Ready")
    logger.info(f"  Groq base: {settings.groq_base_url}")
    logger.info(f"  Reasoning model: {settings.model_reasoning}")
    logger.info(f"  Synthesis model: {settings.model_synthesis}")
    logger.info(f"  Refiner model:   {settings.model_refiner}")
    logger.info(f"  Tavily fallback: {'configured' if settings.tavily_api_key else 'NOT SET'}")
    logger.info("=" * 60)

    yield  # App is running

    # Cleanup
    logger.info("Shutting down Engineering Oracle backend...")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Engineering Oracle",
        description="Multi-Agent RAG Research & Benchmark Engine",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "https://*.vercel.app",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom error handling middleware
    app.add_middleware(ErrorHandlingMiddleware)

    # Routes
    app.include_router(chat_router, tags=["chat"])
    app.include_router(reports_router, tags=["reports"])

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "service": "engineering-oracle"}

    return app


app = create_app()
