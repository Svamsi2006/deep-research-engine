"""Node 5 — Evaluation: score reasoning output relevance via embeddings."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.graph.models import NodeName, ThoughtEvent
from app.graph.state import OracleState
from app.tools.evaluator import evaluate_relevance

logger = logging.getLogger(__name__)


def evaluation_node(state: OracleState) -> dict:
    """
    Score the reasoning output against the original query using
    cosine similarity of sentence-transformer embeddings.

    The supervisor node will use this score to decide:
      - score >= 0.8 → proceed to synthesis
      - score < 0.8 and retries left → re-run discovery with refined query
      - score < 0.8 and retries exhausted → forced synthesis with warning
    """
    settings = get_settings()
    query = state["query"]
    reasoning = state.get("reasoning_output", "")
    thoughts: list[ThoughtEvent] = []

    thoughts.append(
        ThoughtEvent(
            node=NodeName.EVALUATION,
            message="Computing relevance score (cosine similarity)...",
            status="running",
        )
    )

    score = evaluate_relevance(query, reasoning)

    # Determine what will happen next
    retry_count = state.get("retry_count", 0)
    if score >= settings.relevance_threshold:
        verdict = f"Score {score:.3f} ≥ {settings.relevance_threshold} — proceeding to synthesis"
        status = "completed"
    elif retry_count < settings.max_retries:
        verdict = (
            f"Score {score:.3f} < {settings.relevance_threshold} — "
            f"triggering retry {retry_count + 1}/{settings.max_retries} with refined query"
        )
        status = "running"
    else:
        verdict = (
            f"Score {score:.3f} < {settings.relevance_threshold} — "
            f"retries exhausted ({retry_count}/{settings.max_retries}). Forcing synthesis with quality warning."
        )
        status = "completed"

    thoughts.append(
        ThoughtEvent(
            node=NodeName.EVALUATION,
            message=verdict,
            status=status,
        )
    )

    logger.info(f"Evaluation: score={score:.3f}, retry_count={retry_count}, verdict={verdict}")

    return {
        "evaluation_score": score,
        "thought_trace": thoughts,
        "active_node": NodeName.EVALUATION.value,
    }
