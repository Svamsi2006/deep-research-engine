"""Search tools — DuckDuckGo (via LangChain) + Tavily with robust fallback."""

from __future__ import annotations

import logging
from typing import Optional

from langchain_core.tools import tool

from app.config import get_settings
from app.graph.models import SearchResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DuckDuckGo — uses LangChain's battle-tested DuckDuckGoSearchRun wrapper
# ---------------------------------------------------------------------------


def _ddg_search(query: str, max_results: int = 10) -> list[dict]:
    """Search the web with DuckDuckGo via LangChain. Returns list of dicts."""
    try:
        from langchain_community.tools import DuckDuckGoSearchResults
    except ImportError:
        logger.error("langchain-community not installed — DDG search unavailable")
        return []

    results: list[dict] = []
    try:
        ddg = DuckDuckGoSearchResults(num_results=max_results)
        raw = ddg.invoke(query)

        # DuckDuckGoSearchResults returns a string of dicts; parse it
        if isinstance(raw, str):
            import ast
            try:
                parsed = ast.literal_eval(raw)
            except (ValueError, SyntaxError):
                # Fallback: treat entire string as one snippet
                parsed = [{"snippet": raw, "title": query, "link": ""}]
        elif isinstance(raw, list):
            parsed = raw
        else:
            parsed = []

        for r in parsed:
            if isinstance(r, dict):
                results.append(
                    SearchResult(
                        title=r.get("title", ""),
                        url=r.get("link", r.get("href", "")),
                        snippet=r.get("snippet", r.get("body", "")),
                        source="duckduckgo",
                    ).model_dump()
                )

        logger.info(f"DuckDuckGo returned {len(results)} results for: {query[:60]}")
    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")
    return results


def _ddg_simple(query: str) -> str:
    """Simple DuckDuckGo text search — returns plain text snippet."""
    try:
        from langchain_community.tools import DuckDuckGoSearchRun
        search = DuckDuckGoSearchRun()
        return search.invoke(query)
    except Exception as e:
        logger.warning(f"DuckDuckGo simple search failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Tavily
# ---------------------------------------------------------------------------


def _tavily_search(query: str, max_results: int = 10) -> list[dict]:
    """Search using Tavily API. Returns a list of search result dicts."""
    settings = get_settings()
    key = settings.web_search_api_key or settings.tavily_api_key
    if not key:
        logger.warning("Tavily API key not set — skipping.")
        return []

    try:
        from tavily import TavilyClient

        client = TavilyClient(api_key=key)
        response = client.search(
            query=query,
            max_results=max_results,
            topic=settings.web_search_topic or "general",
            search_depth="advanced" if settings.web_search_advanced else "basic",
        )

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
        logger.info(f"Tavily returned {len(results)} results for: {query[:60]}")
        return results
    except Exception as e:
        logger.warning(f"Tavily search failed: {e}")
        return []


# ---------------------------------------------------------------------------
# LangChain @tool wrappers (for backward compat if anything invokes them)
# ---------------------------------------------------------------------------

@tool
def duckduckgo_search(query: str, max_results: int = 10) -> list[dict]:
    """Search the web with DuckDuckGo. Returns a list of search results."""
    return _ddg_search(query, max_results)


@tool
def tavily_search(query: str, max_results: int = 10) -> list[dict]:
    """Search using Tavily API. Returns a list of search results."""
    return _tavily_search(query, max_results)


# ---------------------------------------------------------------------------
# Helper: quality filter
# ---------------------------------------------------------------------------

def filter_quality_results(
    results: list[SearchResult],
    min_snippet_length: int = 100,
) -> list[SearchResult]:
    """Return only results with sufficiently long snippets."""
    return [r for r in results if len(r.snippet) >= min_snippet_length]


def search_web(query: str, max_results: int = 10) -> list[dict]:
    """
    Provider-aware web search with robust fallback chain.

    Order: configured provider → DuckDuckGo → Tavily.
    Always tries the next if the current returns 0 results.
    """
    settings = get_settings()
    provider = (settings.web_search_provider or "duckduckgo").lower()
    errors: list[str] = []

    # ── Try 1: Tavily first (when selected) ──────────────────────────
    if provider == "tavily":
        results = _tavily_search(query, max_results)
        if results:
            return results
        errors.append("Tavily returned 0 results")

    # ── Try 2: DuckDuckGo ────────────────────────────────────────────
    ddg_results = _ddg_search(query, max_results)
    if ddg_results:
        return ddg_results
    errors.append("DuckDuckGo structured returned 0 results")

    # Simple DDG fallback — returns plain text, wrap as single result
    simple = _ddg_simple(query)
    if simple and len(simple) > 50:
        logger.info(f"DDG simple fallback returned {len(simple)} chars")
        return [
            SearchResult(
                title=query,
                url="",
                snippet=simple[:1500],
                source="duckduckgo",
            ).model_dump()
        ]
    errors.append("DuckDuckGo simple also returned 0 results")

    # ── Try 3: Tavily fallback (if DDG was primary) ──────────────────
    if provider != "tavily":
        results = _tavily_search(query, max_results)
        if results:
            return results
        errors.append("Tavily fallback also returned 0 results")

    logger.warning(f"All web search providers failed for '{query[:60]}': {'; '.join(errors)}")
    return []
