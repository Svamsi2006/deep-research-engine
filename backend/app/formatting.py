"""Output formatting — Perplexity-style answers with inline citations."""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def format_answer_with_sources(
    answer_text: str,
    sources: list[dict],
    confidence: float = 1.0,
    search_results: Optional[list[dict]] = None
) -> dict:
    """
    Format an answer in Perplexity-style with inline citations.
    
    Args:
        answer_text: Main answer text
        sources: List of sources used (from DB or web search)
        confidence: Confidence score (0-1)
        search_results: Optional web search results for reference
    
    Returns:
        Dict with formatted answer, citations, and sources
    """
    
    # Create source index
    source_index = {}
    for i, source in enumerate(sources, 1):
        source_id = source.get("id") or source.get("url") or source.get("title")
        source_index[source_id] = i
    
    # Add citation numbers to answer
    formatted_answer = answer_text
    for i, source in enumerate(sources, 1):
        source_id = source.get("id") or source.get("url") or source.get("title")
        # Could improve this with more sophisticated matching
        formatted_answer = formatted_answer.replace(
            f"[{source_id}]",
            f"[{i}]"
        )
    
    # Build sources section
    sources_html = ""
    for i, source in enumerate(sources, 1):
        title = source.get("title") or source.get("name") or "Untitled"
        url = source.get("url") or source.get("origin") or ""
        source_type = source.get("type") or source.get("source_type") or "document"
        
        sources_html += f"\n[{i}] **{title}** ({source_type})"
        if url:
            sources_html += f"\n    {url}"
    
    # Add web search results as additional sources if provided
    if search_results:
        for i, result in enumerate(search_results, len(sources) + 1):
            title = result.get("title") or "Search Result"
            url = result.get("url") or ""
            snippet = result.get("snippet") or ""
            
            sources_html += f"\n[{i}] **{title}**"
            if url:
                sources_html += f"\n    {url}"
            if snippet:
                sources_html += f"\n    {snippet[:200]}..."
    
    return {
        "answer": formatted_answer,
        "sources": sources_html.strip(),
        "source_count": len(sources) + (len(search_results) if search_results else 0),
        "confidence": confidence,
        "sources_raw": sources,
        "search_results": search_results or [],
    }
