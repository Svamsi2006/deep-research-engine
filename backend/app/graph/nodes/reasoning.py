"""Node 4 — Reasoning: Groq-hosted LLM analyses engineering data for metrics."""

from __future__ import annotations

import logging
import uuid

from app.config import get_settings
from app.graph.models import Chunk, NodeName, ThoughtEvent
from app.graph.state import OracleState
from app.tools.evaluator import query_chunks

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Collection name helper (must match clean.py)
# ---------------------------------------------------------------------------

def _collection_name(query: str) -> str:
    slug = query.lower().replace(" ", "_")[:40]
    safe = "".join(c for c in slug if c.isalnum() or c in "_-")
    return f"oracle_{safe}" if len(safe) >= 3 else f"oracle_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# System prompt for the reasoning model
# ---------------------------------------------------------------------------

REASONING_SYSTEM = """\
You are a senior ML/systems engineer performing a technical analysis.

Given the collected research data below, extract and organize:
1. **Performance Metrics**: FLOPs, latency (ms), throughput (tokens/s), memory usage (GB)
2. **Architecture Details**: Key design choices, parameter counts, layer configurations
3. **Code Patterns**: Notable implementation patterns, framework usage, API design
4. **Comparative Analysis**: Direct head-to-head comparisons where data exists
5. **Trade-offs**: Strengths, weaknesses, and production readiness signals

Be precise with numbers. Cite the source document for each claim.
If data is missing or conflicting, say so explicitly — do NOT fabricate metrics.
Output your analysis as structured Markdown with clear section headers.
"""


def reasoning_node(state: OracleState) -> dict:
    """
    Use Groq-hosted LLM to analyze the collected and chunked data.

    Retrieves the most relevant chunks from ChromaDB, feeds them as context,
    and requests a structured technical analysis.
    """
    settings = get_settings()
    query = state.get("refined_query") or state["query"]
    thoughts: list[ThoughtEvent] = []

    # ── Retrieve relevant chunks from ChromaDB ────────────────────────
    collection_name = _collection_name(state["query"])
    thoughts.append(
        ThoughtEvent(
            node=NodeName.REASONING,
            message="Retrieving top-k relevant chunks from ChromaDB...",
            status="running",
        )
    )

    retrieved: list[str] = []
    try:
        retrieved = query_chunks(collection_name, query, n_results=15)
    except Exception as e:
        logger.warning(f"ChromaDB retrieval failed: {e}")

    # Fallback: use raw chunks from state if ChromaDB fails
    if not retrieved:
        chunks: list[Chunk] = state.get("cleaned_chunks", [])
        retrieved = [c.content for c in chunks[:15]]

    thoughts.append(
        ThoughtEvent(
            node=NodeName.REASONING,
            message=f"Retrieved {len(retrieved)} context chunks for analysis",
            status="completed",
        )
    )

    # ── Build the prompt ──────────────────────────────────────────────
    context_block = "\n\n---\n\n".join(
        f"[Source {i+1}]\n{chunk}" for i, chunk in enumerate(retrieved)
    )

    user_prompt = f"""\
## Research Query
{query}

## Collected Sources ({len(retrieved)} chunks)
{context_block}

## Task
Perform a thorough technical analysis of the above sources in relation to the query.
Follow the analysis framework in your system instructions.
"""

    # ── Call reasoning model via Groq ─────────────────────────────────
    thoughts.append(
        ThoughtEvent(
            node=NodeName.REASONING,
            message=f"Invoking {settings.model_reasoning} for technical analysis...",
            status="running",
        )
    )

    from openai import OpenAI

    client = OpenAI(
        base_url=settings.groq_base_url,
        api_key=settings.groq_api_key,
    )

    try:
        response = client.chat.completions.create(
            model=settings.model_reasoning,
            messages=[
                {"role": "system", "content": REASONING_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
            temperature=0.3,
        )
        reasoning_output = response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Reasoning model call failed: {e}")
        reasoning_output = f"## Analysis Error\n\nThe reasoning model failed: {e}\n\nFalling back to raw data summary.\n\n{context_block[:3000]}"
        thoughts.append(
            ThoughtEvent(
                node=NodeName.REASONING,
                message=f"Model call failed: {e}",
                status="error",
            )
        )

    thoughts.append(
        ThoughtEvent(
            node=NodeName.REASONING,
            message=f"Analysis complete ({len(reasoning_output)} chars)",
            status="completed",
        )
    )

    logger.info(f"Reasoning complete: {len(reasoning_output)} chars")

    return {
        "reasoning_output": reasoning_output,
        "thought_trace": thoughts,
        "active_node": NodeName.REASONING.value,
    }
