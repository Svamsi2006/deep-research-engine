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
    openrouter_model: str = "meta-llama/llama-3.3-70b-instruct:free"
    model_router: str = "openai/gpt-4o-mini"
    model_refiner: str = "openai/gpt-4o-mini"
    model_fast: str = "openai/gpt-4o-mini"
    model_reasoning: str = "openai/gpt-4o-mini"
    model_synthesis: str = "openai/gpt-4o-mini"

    # ── Groq (fallback) ───────────────────────────────────────────────
    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model: str = "llama-3.3-70b-versatile"

    # ── Tavily (optional web search) ──────────────────────────────────
    tavily_api_key: str = ""

    # ── Optional provider keys (for dynamic runtime selection) ───────
    openai_api_key: str = ""
    google_api_key: str = ""
    deepseek_api_key: str = ""
    grok_api_key: str = ""

    # ── Dynamic Provider Settings (UI configurable) ───────────────────
    ai_provider: str = "openrouter"  # ollama/openai/gemini/deepseek/openrouter/grok/groq
    ai_api_key: str = ""
    ai_api_base_url: str = ""
    ai_model: str = ""
    ai_context_length: int = 128000

    web_search_provider: str = "tavily"  # tavily/firecrawl/duckduckgo
    web_search_api_key: str = ""
    web_search_concurrency_limit: int = 2
    web_search_advanced: bool = False
    web_search_topic: str = "general"  # general/news/finance

    # ── Retrieval / quality routing ────────────────────────────────────
    relevance_threshold: float = 0.8
    max_retries: int = 2
    min_quality_results: int = 3

    # ── Embeddings / vector store ─────────────────────────────────────
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    cohere_api_key: str = ""
    
    # ── Pinecone Vector Database ────────────────────────────────────────
    pinecone_api_key: str = ""
    pinecone_environment: str = "us-east-1"
    pinecone_index_name: str = "deep-research-oracle"
    pinecone_dimension: int = 384  # all-MiniLM-L6-v2 output dimension
    
    # ── GitHub Access ──────────────────────────────────────────────────
    github_token: str = ""

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


def reload_settings() -> Settings:
    """Clear cache and reload settings (used after .env updates)."""
    get_settings.cache_clear()
    return get_settings()
