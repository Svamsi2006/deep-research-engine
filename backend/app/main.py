"""FastAPI application entry point — Deep Research Platform."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    settings = get_settings()

    # Initialize database
    from app.database import init_db

    logger.info("Initializing SQLite database...")
    await init_db(settings.database_url)

    logger.info("=" * 60)
    logger.info("  Deep Research Platform — Backend Ready")
    logger.info(f"  OpenRouter: {'configured' if settings.openrouter_api_key else '⚠️ NOT SET'}")
    logger.info(f"  Groq:       {'configured' if settings.groq_api_key else '⚠️ NOT SET'}")
    logger.info(f"  Model:      {settings.openrouter_model} (primary)")
    logger.info(f"  Fallback:   {settings.groq_model} (groq)")
    logger.info(f"  Tavily:     {'configured' if settings.tavily_api_key else 'NOT SET'}")
    logger.info("=" * 60)

    yield  # App is running

    logger.info("Backend shutting down")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Deep Research Platform",
    version="0.2.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global error handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


# Health check
@app.get("/health")
async def health():
    settings = get_settings()
    return {
        "status": "healthy",
        "version": "0.2.0",
        "openrouter": bool(settings.openrouter_api_key),
        "groq": bool(settings.groq_api_key),
    }


# Register routes
from app.routes.chat import router as chat_router
from app.routes.ingest import router as ingest_router

app.include_router(chat_router, prefix="/api")
app.include_router(ingest_router, prefix="/api")
