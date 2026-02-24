"""Search tools — DuckDuckGo (primary) + Tavily (fallback)."""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import get_settings
from app.graph.models import SearchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DuckDuckGo (Primary)
# ---------------------------------------------------------------------------

@tool
def duckduckgo_search(query: str, max_results: int = 10) -> list[dict]:
    """Search the web with DuckDuckGo. Returns a list of search results."""
    from duckduckgo_search import DDGS

    results: list[dict] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("href", r.get("link", "")),
                        snippet=r.get("body", ""),
                        source="duckduckgo",
                    ).model_dump()
                )
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
    return results


# ---------------------------------------------------------------------------
# Tavily (Fallback)
# ---------------------------------------------------------------------------

@tool
def tavily_search(query: str, max_results: int = 10) -> list[dict]:
    """Fallback search using Tavily API. Returns a list of search results."""
    settings = get_settings()
    if not settings.tavily_api_key:
        logger.warning("Tavily API key not set — skipping fallback search.")
        return []

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query=query, max_results=max_results)

        results: list[dict] = []
        for r in response.get("results", []):
            results.append(
                SearchResult(
                    title=r.get("title", ""),
                    url=r.get("url", ""),
                    snippet=r.get("content", ""),
                    source="tavily",
                    relevance_score=r.get("score", 0.0),
                ).model_dump()
            )
        return results
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return []


# ---------------------------------------------------------------------------
# Helper: quality filter
# ---------------------------------------------------------------------------

def filter_quality_results(
    results: list[SearchResult],
    min_snippet_length: int = 100,
) -> list[SearchResult]:
    """Return only results with sufficiently long snippets."""
    return [r for r in results if len(r.snippet) >= min_snippet_length]
