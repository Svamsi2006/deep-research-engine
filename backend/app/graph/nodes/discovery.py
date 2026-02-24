"""Node 1 — Discovery: DuckDuckGo search with Tavily fallback."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.graph.models import NodeName, SearchResult, ThoughtEvent
from app.graph.state import OracleState
from app.tools.search import duckduckgo_search, filter_quality_results, tavily_search

logger = logging.getLogger(__name__)


def discovery_node(state: OracleState) -> dict:
    """
    Search the web for the user's query.

    Strategy:
      1. Run DuckDuckGo search.
      2. Filter for quality (snippet > 100 chars).
      3. If < min_quality_results, fall back to Tavily.
    """
    settings = get_settings()
    query = state.get("refined_query") or state["query"]
    thoughts: list[ThoughtEvent] = []
    all_results: list[SearchResult] = []

    # ── DuckDuckGo ────────────────────────────────────────────────────
    thoughts.append(
        ThoughtEvent(
            node=NodeName.DISCOVERY,
            message=f"Searching DuckDuckGo for: \"{query}\"",
            status="running",
        )
    )

    raw = duckduckgo_search.invoke({"query": query, "max_results": 10})
    ddg_results = [SearchResult(**r) for r in raw]
    quality = filter_quality_results(ddg_results)

    thoughts.append(
        ThoughtEvent(
            node=NodeName.DISCOVERY,
            message=f"DuckDuckGo returned {len(ddg_results)} results ({len(quality)} high-quality)",
            status="completed",
        )
    )

    all_results.extend(ddg_results)

    # ── Tavily fallback ───────────────────────────────────────────────
    if len(quality) < settings.min_quality_results:
        thoughts.append(
            ThoughtEvent(
                node=NodeName.DISCOVERY,
                message=f"Quality results below threshold ({len(quality)}<{settings.min_quality_results}). Falling back to Tavily...",
                status="running",
            )
        )

        tavily_raw = tavily_search.invoke({"query": query, "max_results": 10})
        tavily_results = [SearchResult(**r) for r in tavily_raw]
        all_results.extend(tavily_results)

        thoughts.append(
            ThoughtEvent(
                node=NodeName.DISCOVERY,
                message=f"Tavily returned {len(tavily_results)} additional results",
                status="completed",
            )
        )
    else:
        thoughts.append(
            ThoughtEvent(
                node=NodeName.DISCOVERY,
                message="Sufficient quality results from DuckDuckGo — skipping Tavily",
                status="completed",
            )
        )

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique: list[SearchResult] = []
    for r in all_results:
        if r.url not in seen_urls:
            seen_urls.add(r.url)
            unique.append(r)

    logger.info(f"Discovery complete: {len(unique)} unique results")

    return {
        "search_results": unique,
        "thought_trace": thoughts,
        "active_node": NodeName.DISCOVERY.value,
    }
