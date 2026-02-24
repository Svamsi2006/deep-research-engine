"""Deep Report Pipeline — deterministic: Planner → Retrieve → Write → Judge → Refine.

Each step streams SSE thought events for the timeline UI.
Uses the LLM Gateway (OpenRouter → Groq failover) for all LLM calls.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.config import get_settings
from app.llm_gateway import call_llm
from app.tools.indexer import IndexChunk, BM25Index, build_index, SearchResult

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class PipelineStep:
    """A single step in the pipeline timeline."""
    name: str
    status: str = "pending"  # pending, running, completed, error
    message: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict:
        return {
            "node": self.name,
            "status": self.status,
            "message": self.message,
            "timestamp": self.timestamp or datetime.utcnow().isoformat(),
        }


@dataclass
class PipelineResult:
    """Output of the deep report pipeline."""
    report_md: str = ""
    sources_used: list[dict] = field(default_factory=list)
    evaluation_score: float = 0.0
    steps: list[PipelineStep] = field(default_factory=list)
    need_more_sources: bool = False
    need_more_message: str = ""


# ---------------------------------------------------------------------------
# Step 1: Planner
# ---------------------------------------------------------------------------

PLANNER_SYSTEM = """\
You are a research planning assistant. Given a user's engineering question and available source descriptions, generate a research plan.

Output ONLY valid JSON (no markdown, no explanation):
{
  "sub_questions": ["question1", "question2", ...],
  "must_check": ["baseline metrics", "failure modes", "implementation gotchas", ...],
  "report_title": "A good title for the report",
  "sufficient_sources": true/false
}

Rules:
- Generate 3-6 focused sub-questions that break down the main question
- Include must-check items: baselines, eval metrics, failure modes, implementation gotchas
- Set sufficient_sources to false if the available sources seem insufficient for a thorough answer
"""


def _plan(question: str, source_summaries: list[str]) -> dict:
    """Generate a research plan with sub-questions."""
    sources_text = "\n".join(f"- {s}" for s in source_summaries) if source_summaries else "(no sources provided)"

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": f"Question: {question}\n\nAvailable sources:\n{sources_text}"},
    ]

    result = call_llm(messages, purpose="planner", max_tokens=512, temperature=0.2)

    try:
        # Clean markdown wrapping if present
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Planner returned non-JSON: {result.text[:200]}")
        return {
            "sub_questions": [question],
            "must_check": [],
            "report_title": question,
            "sufficient_sources": len(source_summaries) > 0,
        }


# ---------------------------------------------------------------------------
# Step 2: Retrieve (no LLM)
# ---------------------------------------------------------------------------


def _retrieve(
    sub_questions: list[str],
    must_check: list[str],
    index: BM25Index,
    top_k: int = 10,
) -> list[SearchResult]:
    """BM25 retrieval for each sub-question. Deduplicates results."""
    seen_ids: set[str] = set()
    all_results: list[SearchResult] = []

    queries = sub_questions + must_check

    for q in queries:
        hits = index.search(q, top_k=top_k)
        for hit in hits:
            if hit.chunk_id not in seen_ids:
                seen_ids.add(hit.chunk_id)
                all_results.append(hit)

    # Sort by score descending
    all_results.sort(key=lambda r: r.score, reverse=True)
    return all_results


# ---------------------------------------------------------------------------
# Step 3: Writer
# ---------------------------------------------------------------------------

WRITER_SYSTEM = """\
You are a senior technical writer producing an engineering research report.

RULES:
- Every factual claim MUST cite its source as [source_id:chunk_id]
- If evidence is insufficient for a claim, say "⚠️ Insufficient evidence"
- Use tables for numeric comparisons
- Include code blocks with language specifiers
- Be thorough but concise (2000-4000 words target)

REPORT STRUCTURE:
1. Title + Problem Restatement
2. Sources Used (bullets, each with URL/filename)
3. Findings (bullets, each with citation)
4. How It Works (short technical explanation)
5. Engineering Trade-offs (table)
6. Implementation Notes (with code pointers)
7. Risks / Failure Modes
8. Next Experiments (what to test)
"""


def _write_report(
    question: str,
    plan: dict,
    retrieved: list[SearchResult],
    source_titles: dict[str, str],
) -> str:
    """Write the full report using retrieved evidence."""
    # Build evidence context
    evidence_blocks = []
    for r in retrieved[:30]:  # Cap at 30 chunks
        src_name = source_titles.get(r.source_id, r.source_id[:8])
        evidence_blocks.append(
            f"[{r.source_id[:8]}:{r.chunk_id[:8]}] (from: {src_name}, section: {r.section_heading})\n{r.content}"
        )

    evidence_text = "\n\n---\n\n".join(evidence_blocks) if evidence_blocks else "(no evidence retrieved)"

    user_prompt = f"""\
## Research Question
{question}

## Report Title
{plan.get('report_title', question)}

## Sub-questions to Address
{chr(10).join(f"- {q}" for q in plan.get('sub_questions', [question]))}

## Must-check Items
{chr(10).join(f"- {item}" for item in plan.get('must_check', []))}

## Retrieved Evidence ({len(retrieved)} chunks)
{evidence_text}

## Sources Available
{chr(10).join(f"- [{sid[:8]}] {title}" for sid, title in source_titles.items())}

Write the complete engineering report following the structure in your system instructions.
Cite every claim using [source_id:chunk_id] format.
"""

    result = call_llm(
        [
            {"role": "system", "content": WRITER_SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        purpose="writer",
        max_tokens=4096,
        temperature=0.3,
    )

    return result.text


# ---------------------------------------------------------------------------
# Step 4: Judge
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """\
You are a report quality judge. Evaluate the engineering report below.

Output ONLY valid JSON:
{
  "score": 0.0-1.0,
  "pass": true/false,
  "issues": ["issue1", "issue2", ...],
  "missing_citations": ["claim without citation", ...],
  "shallow_sections": ["section name", ...],
  "needs_comparison_table": true/false
}

Scoring:
- 0.9+: Excellent, thorough, well-cited
- 0.7-0.9: Good but has some gaps
- 0.5-0.7: Mediocre, missing important aspects
- Below 0.5: Poor, needs significant rework

Set pass=true if score >= 0.7
"""


def _judge(question: str, report: str) -> dict:
    """Judge the report quality."""
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": f"Question: {question}\n\nReport:\n{report[:6000]}"},
    ]

    result = call_llm(messages, purpose="judge", max_tokens=512, temperature=0.1)

    try:
        text = result.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"Judge returned non-JSON: {result.text[:200]}")
        return {"score": 0.7, "pass": True, "issues": [], "missing_citations": [], "shallow_sections": []}


# ---------------------------------------------------------------------------
# Step 5: Refine (only if judge fails)
# ---------------------------------------------------------------------------

REFINE_SYSTEM = """\
You are a report editor. The judge found issues with the report below.
Fix ONLY the flagged sections. Keep all existing good content unchanged.
Return the complete improved report.
"""


def _refine(report: str, judge_result: dict) -> str:
    """Refine flagged sections of the report."""
    issues_text = json.dumps(judge_result, indent=2)

    result = call_llm(
        [
            {"role": "system", "content": REFINE_SYSTEM},
            {"role": "user", "content": f"Issues found:\n{issues_text}\n\nOriginal report:\n{report}"},
        ],
        purpose="refiner",
        max_tokens=4096,
        temperature=0.3,
    )

    return result.text


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


def run_deep_report(
    question: str,
    chunks: list[IndexChunk],
    source_titles: dict[str, str],
    allow_web_search: bool = False,
    depth: str = "deep",
) -> tuple[PipelineResult, list[dict]]:
    """
    Execute the full deep report pipeline.

    Returns (PipelineResult, list_of_step_events_for_SSE)
    """
    steps: list[dict] = []
    result = PipelineResult()

    def emit(name: str, message: str, status: str = "running"):
        step = {"node": name, "message": message, "status": status, "timestamp": datetime.utcnow().isoformat()}
        steps.append(step)
        result.steps.append(PipelineStep(name=name, message=message, status=status))

    # ── Step 1: Plan ──────────────────────────────────────────────────
    emit("planner", "📋 Generating research plan and sub-questions...")

    source_summaries = [f"{title} ({sid[:8]})" for sid, title in source_titles.items()]
    plan = _plan(question, source_summaries)

    sub_qs = plan.get("sub_questions", [question])
    must_check = plan.get("must_check", [])
    sufficient = plan.get("sufficient_sources", True)

    emit("planner", f"Plan ready: {len(sub_qs)} sub-questions, {len(must_check)} must-check items", "completed")

    # Check if sources are sufficient
    if not sufficient and not allow_web_search and len(chunks) == 0:
        result.need_more_sources = True
        result.need_more_message = (
            "The available sources appear insufficient for a thorough answer. "
            "Please add more PDFs, URLs, or enable web search."
        )
        emit("planner", "⚠️ Need more sources — insufficient evidence", "error")
        return result, steps

    # ── Step 2: Retrieve ──────────────────────────────────────────────
    emit("retrieval", f"🔍 Searching {len(chunks)} chunks for relevant evidence...")

    index = build_index(chunks)
    settings = get_settings()
    retrieved = _retrieve(sub_qs, must_check, index, top_k=settings.retrieval_top_k)

    emit("retrieval", f"Found {len(retrieved)} relevant chunks", "completed")

    # Track sources used
    used_source_ids = set(r.source_id for r in retrieved)
    result.sources_used = [
        {"source_id": sid, "title": source_titles.get(sid, "Unknown")}
        for sid in used_source_ids
    ]

    # ── Step 3: Write ─────────────────────────────────────────────────
    emit("writer", "✍️ Writing engineering report with citations...")

    report = _write_report(question, plan, retrieved, source_titles)

    emit("writer", f"Report drafted ({len(report)} chars, ~{len(report.split())} words)", "completed")

    # ── Step 4: Judge ─────────────────────────────────────────────────
    emit("judge", "🔍 Verifying report quality and citations...")

    judge_result = _judge(question, report)
    score = judge_result.get("score", 0.7)
    passed = judge_result.get("pass", True)

    issues = judge_result.get("issues", [])
    emit("judge", f"Score: {score:.0%} — {len(issues)} issues found", "completed")

    # ── Step 5: Refine (if needed) ────────────────────────────────────
    if not passed and depth == "deep":
        emit("refiner", "🔧 Refining flagged sections...")

        report = _refine(report, judge_result)

        # Re-judge
        judge_result2 = _judge(question, report)
        score = judge_result2.get("score", score)

        emit("refiner", f"Refined. New score: {score:.0%}", "completed")

    result.report_md = report
    result.evaluation_score = score

    emit("done", f"✅ Report complete — quality score: {score:.0%}", "completed")

    return result, steps
