"""Application configuration via pydantic-settings. Reads from .env file."""

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

    # ── OpenRouter (primary — free models) ────────────────────────────
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "deepseek/deepseek-chat-v3-0324:free"

    # ── Groq (fallback) ───────────────────────────────────────────────
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Tavily (optional web search) ──────────────────────────────────
    tavily_api_key: str = ""

    # ── Database ──────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./oracle.db"

    # ── Backend ───────────────────────────────────────────────────────
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    # ── Pipeline tuning ───────────────────────────────────────────────
    chunk_size: int = 600            # Target tokens per chunk (400-800)
    chunk_overlap: int = 100         # Overlap between chunks
    retrieval_top_k: int = 10        # BM25 top-k per sub-question
    max_scrape_urls: int = 8         # Cap parallel URL scrapes


@lru_cache
def get_settings() -> Settings:
    return Settings()
