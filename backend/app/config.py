"""Application configuration via pydantic-settings.  Reads from .env file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve .env from project root (one level up from backend/)
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Groq Cloud ────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"

    # Model identifiers (Groq Cloud)
    model_reasoning: str = "llama-3.1-8b-instant"
    model_synthesis: str = "llama-3.3-70b-versatile"
    model_refiner: str = "gemma2-9b-it"

    # ── Tavily ────────────────────────────────────────────────────────
    tavily_api_key: str = ""

    # ── ChromaDB ──────────────────────────────────────────────────────
    chroma_host: str = "localhost"
    chroma_port: int = 8001

    # ── Database ──────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./oracle.db"

    # ── Backend ───────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ── Pipeline tuning ───────────────────────────────────────────────
    min_quality_results: int = 3         # Minimum usable search results
    relevance_threshold: float = 0.8     # Cosine similarity cutoff
    max_retries: int = 2                 # Re-search attempts before forced synthesis
    chunk_size: int = 2000               # Text splitter chunk size
    chunk_overlap: int = 200             # Text splitter overlap
    max_scrape_urls: int = 8             # Cap parallel scrapes
    embedding_model: str = "all-MiniLM-L6-v2"


@lru_cache
def get_settings() -> Settings:
    return Settings()
