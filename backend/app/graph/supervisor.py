"""Supervisor — conditional routing logic for the Evaluation → next node decision."""

from __future__ import annotations

import logging

from app.config import get_settings
from app.graph.models import NodeName, ThoughtEvent
from app.graph.state import OracleState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Query refinement (called on retry)
# ---------------------------------------------------------------------------

def _refine_query(original_query: str, reasoning_output: str) -> str:
    """
    Use Gemini 2.0 Flash via OpenRouter to generate a better search query
    when the first attempt scored below the relevance threshold.
    """
    settings = get_settings()

    from openai import OpenAI

    client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )

    try:
        response = client.chat.completions.create(
            model=settings.model_refiner,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a search query optimizer. Given an original query and "
                        "a summary of what was found, generate a single improved search "
                        "query that will find MORE RELEVANT and SPECIFIC technical results. "
                        "Return ONLY the new query string, nothing else."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Original query: {original_query}\n\n"
                        f"What we found (summary):\n{reasoning_output[:1500]}\n\n"
                        "Generate an improved, more specific search query:"
                    ),
                },
            ],
            max_tokens=200,
            temperature=0.5,
        )
        refined = response.choices[0].message.content or original_query
        return refined.strip().strip('"').strip("'")
    except Exception as e:
        logger.warning(f"Query refinement failed: {e}")
        return original_query + " benchmark comparison production"


# ---------------------------------------------------------------------------
# Supervisor conditional edge
# ---------------------------------------------------------------------------

def supervisor(state: OracleState) -> str:
    """
    Conditional edge function for LangGraph.

    Decides the next node after Evaluation:
      - "synthesis" if score >= threshold
      - "discovery" if score < threshold and retries remain
      - "synthesis" (forced) if retries exhausted
    """
    settings = get_settings()
    score = state.get("evaluation_score", 0.0)
    retry_count = state.get("retry_count", 0)

    if score >= settings.relevance_threshold:
        logger.info(f"Supervisor: score {score:.3f} ≥ {settings.relevance_threshold} → synthesis")
        return "synthesis"
    elif retry_count < settings.max_retries:
        logger.info(
            f"Supervisor: score {score:.3f} < {settings.relevance_threshold}, "
            f"retry {retry_count + 1}/{settings.max_retries} → discovery"
        )
        return "retry"
    else:
        logger.info(
            f"Supervisor: score {score:.3f} < {settings.relevance_threshold}, "
            f"retries exhausted → forced synthesis"
        )
        return "force_synthesis"


def retry_prep_node(state: OracleState) -> dict:
    """
    Prepare for a retry: refine the query and increment retry counter.
    This node sits between the supervisor's "retry" edge and looping back to discovery.
    """
    query = state["query"]
    reasoning = state.get("reasoning_output", "")
    retry_count = state.get("retry_count", 0)

    refined = _refine_query(query, reasoning)

    thoughts = [
        ThoughtEvent(
            node=NodeName.EVALUATION,
            message=f"Refined query for retry {retry_count + 1}: \"{refined}\"",
            status="running",
        )
    ]

    return {
        "refined_query": refined,
        "retry_count": retry_count + 1,
        "thought_trace": thoughts,
    }


def force_synthesis_prep(state: OracleState) -> dict:
    """Mark quality warning before forced synthesis."""
    return {
        "quality_warning": True,
        "thought_trace": [
            ThoughtEvent(
                node=NodeName.EVALUATION,
                message="⚠️ Quality threshold not met after retries — forcing synthesis with warning flag",
                status="completed",
            )
        ],
    }
