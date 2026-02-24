"""Node 6 — Synthesis: OpenRouter-hosted LLM generates a structured Markdown report."""

from __future__ import annotations

import logging
import uuid

from app.config import get_settings
from app.graph.models import NodeName, ThoughtEvent
from app.graph.state import OracleState
from app.tools.evaluator import query_chunks

logger = logging.getLogger(__name__)


def _collection_name(query: str) -> str:
    slug = query.lower().replace(" ", "_")[:40]
    safe = "".join(c for c in slug if c.isalnum() or c in "_-")
    return f"oracle_{safe}" if len(safe) >= 3 else f"oracle_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Report template
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM = """\
You are a world-class technical writer producing a comprehensive engineering report.

Generate a report with the following structure in valid Markdown:

# {title}

## Executive Summary
A 3-5 sentence overview of key findings.

## Architecture Comparison
Detailed technical comparison with diagrams described in text.

## Benchmarks

| Metric | Option A | Option B | Notes |
|--------|----------|----------|-------|
| FLOPs  | ...      | ...      | ...   |
| Latency| ...      | ...      | ...   |
| Memory | ...      | ...      | ...   |

## Code Examples
Relevant code snippets with syntax highlighting.

## Trade-offs & Recommendations
Production-readiness assessment, scaling considerations.

## Limitations of This Analysis
What data was missing, potential biases.

## Citations
Numbered list of all sources with URLs.

---

RULES:
- Every claim MUST have a citation number [1], [2], etc.
- If data is uncertain or missing, state it explicitly.
- Use tables for all numeric comparisons.
- Code blocks must specify the language.
- Be thorough but concise — target 2000-4000 words.
"""


def synthesis_node(state: OracleState) -> dict:
    """
    Generate the final structured Markdown report using OpenRouter LLM.

    Combines:
      - The reasoning analysis
      - Retrieved source chunks
      - Original search results (for citations)
    """
    settings = get_settings()
    query = state["query"]
    reasoning = state.get("reasoning_output", "")
    quality_warning = state.get("quality_warning", False)
    is_fast = state.get("mode", "fast") == "fast"
    thoughts: list[ThoughtEvent] = []

    # ── Gather context ────────────────────────────────────────────────
    collection_name = _collection_name(query)
    retrieved: list[str] = []
    if not is_fast:
        try:
            retrieved = query_chunks(collection_name, query, n_results=10)
        except Exception:
            pass

    # Build citation list from search results
    search_results = state.get("search_results", [])
    citations = "\n".join(
        f"[{i+1}] {r.title} — {r.url}"
        for i, r in enumerate(search_results)
    )

    # ── Build prompt ──────────────────────────────────────────────────
    quality_note = ""
    if quality_warning:
        quality_note = (
            "\n\n⚠️ NOTE: The evaluation score was below the quality threshold "
            "after maximum retries. Flag any uncertain claims prominently.\n"
        )

    user_prompt = f"""\
## Query
{query}

## Technical Analysis (from reasoning engine)
{reasoning}

## Additional Source Excerpts
{chr(10).join(f"---{chr(10)}{chunk}" for chunk in retrieved[:8])}

## Source Citations
{citations}
{quality_note}
## Task
Write the complete engineering report following your system template.
Include all citations as numbered references.
"""

    model_name = settings.model_fast if is_fast else settings.model_synthesis
    max_tok = 2048 if is_fast else 8192
    thoughts.append(
        ThoughtEvent(
            node=NodeName.SYNTHESIS,
            message=f"Generating report with {model_name} ({'fast' if is_fast else 'deep'} mode)...",
            status="running",
        )
    )

    # ── Call synthesis model via OpenRouter ────────────────────────────
    from openai import OpenAI

    client = OpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
    )

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=max_tok,
            temperature=0.4,
        )
        report = response.choices[0].message.content or ""
    except Exception as e:
        logger.error(f"Synthesis model call failed: {e}")
        report = (
            f"# Report Generation Error\n\n"
            f"The synthesis model failed: {e}\n\n"
            f"## Raw Analysis\n\n{reasoning[:5000]}\n\n"
            f"## Sources\n\n{citations}"
        )
        thoughts.append(
            ThoughtEvent(
                node=NodeName.SYNTHESIS,
                message=f"Model call failed: {e}",
                status="error",
            )
        )

    thoughts.append(
        ThoughtEvent(
            node=NodeName.SYNTHESIS,
            message=f"Report generated ({len(report)} chars, {len(report.split())} words)",
            status="completed",
        )
    )

    logger.info(f"Synthesis complete: {len(report)} chars")

    return {
        "final_report": report,
        "thought_trace": thoughts,
        "active_node": NodeName.SYNTHESIS.value,
    }
