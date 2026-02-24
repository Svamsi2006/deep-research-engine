"""LangGraph shared state definition for the Engineering Oracle pipeline."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from app.graph.models import (
    Chunk,
    RepoInfo,
    ScrapedDocument,
    SearchResult,
    ThoughtEvent,
)


def _merge_lists(left: list, right: list) -> list:
    """Reducer that merges two lists (used by LangGraph annotations)."""
    return left + right


class OracleState(TypedDict, total=False):
    """
    The shared state that flows through every LangGraph node.

    Fields annotated with `Annotated[..., operator.add]` or custom reducers
    are *append-merged* across parallel branches instead of overwritten.
    """

    # ── Input ──────────────────────────────────────────────────────────
    query: str                       # Original user query
    refined_query: str               # Optionally improved by Gemini on retry

    # ── Node 1: Discovery ─────────────────────────────────────────────
    search_results: Annotated[list[SearchResult], _merge_lists]

    # ── Node 2: Harvest ───────────────────────────────────────────────
    scraped_docs: Annotated[list[ScrapedDocument], _merge_lists]
    cloned_repos: Annotated[list[RepoInfo], _merge_lists]

    # ── Node 3: Clean ─────────────────────────────────────────────────
    cleaned_chunks: Annotated[list[Chunk], _merge_lists]

    # ── Node 4: Reasoning ─────────────────────────────────────────────
    reasoning_output: str

    # ── Node 5: Evaluation ────────────────────────────────────────────
    evaluation_score: float

    # ── Node 6: Synthesis ─────────────────────────────────────────────
    final_report: str

    # ── Control flow ──────────────────────────────────────────────────
    retry_count: int                  # Max 2 retries before forced synthesis
    active_node: str                  # Current node name for UI trace
    quality_warning: bool             # True if synthesis forced despite low score
    mode: str                         # "fast" or "thinking"

    # ── Thought trace (streamed to UI via SSE) ────────────────────────
    thought_trace: Annotated[list[ThoughtEvent], _merge_lists]
