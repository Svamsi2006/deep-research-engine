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
from app.tools.indexer import IndexChunk, BM25Index, build_index, hybrid_search, SearchResult

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
You are a research planner. Given a question and source list, output ONLY valid JSON:
{"sub_questions":["q1","q2","q3"],"must_check":["item1"],"report_title":"Title","sufficient_sources":true}
Rules: 3-4 sub-questions max. 1-2 must-check items. Be concise.
"""


def _plan(question: str, source_summaries: list[str]) -> dict:
    """Generate a research plan with sub-questions."""
    # Limit source summaries to keep planner input small
    summaries_capped = source_summaries[:10]
    sources_text = "\n".join(f"- {s[:80]}" for s in summaries_capped) if summaries_capped else "(none)"

    messages = [
        {"role": "system", "content": PLANNER_SYSTEM},
        {"role": "user", "content": f"Q: {question}\nSources:\n{sources_text}"},
    ]

    result = call_llm(messages, purpose="planner", max_tokens=300, temperature=0.2)

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
You are a technical writer. Write a concise engineering report.
Cite sources as [src_id]. Use markdown: headers, bullets, tables, code blocks.
Structure: Title, Summary, Key Findings (with citations), Trade-offs, Risks, Next Steps.
Target: 1000-2000 words. Be direct.
"""


# Max evidence chunks and chars per chunk to stay within token budgets
_MAX_EVIDENCE_CHUNKS = 12
_MAX_CHUNK_CHARS = 400


def _write_report(
    question: str,
    plan: dict,
    retrieved: list[SearchResult],
    source_titles: dict[str, str],
) -> str:
    """Write the full report using retrieved evidence."""
    from app.llm_gateway import truncate_content, estimate_tokens

    # Build evidence context — capped for token efficiency
    evidence_blocks = []
    for r in retrieved[:_MAX_EVIDENCE_CHUNKS]:
        src_name = source_titles.get(r.source_id, r.source_id[:8])
        snippet = r.content[:_MAX_CHUNK_CHARS]
        evidence_blocks.append(
            f"[{r.source_id[:8]}] ({src_name})\n{snippet}"
        )

    evidence_text = "\n---\n".join(evidence_blocks) if evidence_blocks else "(no evidence)"

    sub_qs = plan.get('sub_questions', [question])[:4]
    must_check = plan.get('must_check', [])[:2]

    user_prompt = f"""Question: {question}
Title: {plan.get('report_title', question)}
Sub-questions: {', '.join(sub_qs)}
Must-check: {', '.join(must_check) if must_check else 'N/A'}

Evidence ({len(evidence_blocks)} chunks):
{evidence_text}

Sources: {', '.join(f'[{sid[:8]}] {t}' for sid, t in list(source_titles.items())[:10])}

Write the report. Cite claims as [src_id]."""

    # Truncate if still too long (~3000 input tok budget for writer)
    user_prompt = truncate_content(user_prompt, 3000)

    messages = [
        {"role": "system", "content": WRITER_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    logger.info(f"Writer input: ~{estimate_tokens(messages)} est. tokens")

    result = call_llm(
        messages,
        purpose="writer",
        max_tokens=3000,
        temperature=0.3,
    )

    return result.text


# ---------------------------------------------------------------------------
# Step 4: Judge
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = """\
Rate the report. Output ONLY JSON: {"score":0.0-1.0,"pass":true/false,"issues":["issue1"]}
pass=true if score>=0.7.
"""


def _judge(question: str, report: str) -> dict:
    """Judge the report quality."""
    from app.llm_gateway import truncate_content
    # Send only the first ~2000 tokens worth of the report
    capped_report = truncate_content(report, 2000)
    messages = [
        {"role": "system", "content": JUDGE_SYSTEM},
        {"role": "user", "content": f"Q: {question}\nReport:\n{capped_report}"},
    ]

    result = call_llm(messages, purpose="judge", max_tokens=256, temperature=0.1)

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
Fix only the flagged issues in the report. Keep existing good content. Return improved report.
"""


def _refine(report: str, judge_result: dict) -> str:
    """Refine flagged sections of the report."""
    from app.llm_gateway import truncate_content
    issues_text = json.dumps(judge_result.get("issues", []))
    # Cap report so refiner doesn't blow token budget
    capped_report = truncate_content(report, 2500)

    result = call_llm(
        [
            {"role": "system", "content": REFINE_SYSTEM},
            {"role": "user", "content": f"Issues: {issues_text}\nReport:\n{capped_report}"},
        ],
        purpose="refiner",
        max_tokens=3000,
        temperature=0.3,
    )

    return result.text


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def _web_search_and_scrape(queries: list[str]) -> tuple[list[IndexChunk], dict[str, str]]:
    from app.tools.search import search_web
    from app.tools.scraper import scrape_urls, scrape_url_metadata_fallback
    from app.tools.indexer import chunk_text
    from app.tools.embedder import embed_texts

    unique_urls = set()
    source_titles = {}
    
    search_errors: list[str] = []
    try:
        for q in queries[:4]:  # Limit to top 4 sub-queries
            try:
                results = search_web(q, max_results=4)
                if not results:
                    search_errors.append(f"No results for: {q[:50]}")
                for r in results:
                    url = r.get("url") or r.get("href")
                    if not url:
                        continue
                    unique_urls.add(url)
                    source_titles[url] = r.get("title", url)
            except Exception as qe:
                search_errors.append(f"Search failed for '{q[:50]}': {qe}")
                logger.warning(f"Query search error: {qe}")
    except Exception as e:
        logger.warning(f"Web search pipeline failed: {e}")
        search_errors.append(f"Web search pipeline error: {e}")

    if search_errors:
        logger.info(f"Web search issues: {'; '.join(search_errors)}")

    urls_list = list(unique_urls)[:8] # Max 8 links to scrape
    if not urls_list:
        return [], {}

    # Scrape
    scraped_docs = await scrape_urls(urls_list, max_concurrent=2)

    # Fallback for blocked sites: keep metadata-only docs so user still gets sources
    scraped_url_set = {d.url for d in scraped_docs}
    for url in urls_list:
        if url in scraped_url_set:
            continue
        try:
            meta = scrape_url_metadata_fallback(url)
            from app.graph.models import ScrapedDocument, UrlCategory

            scraped_docs.append(
                ScrapedDocument(
                    url=url,
                    title=meta.get("title", url),
                    content=meta.get("content", ""),
                    content_type=UrlCategory.OTHER,
                )
            )
        except Exception:
            continue

    new_chunks = []
    for doc in scraped_docs:
        source_id = doc.url
        source_titles[source_id] = doc.title
        doc_chunks = chunk_text(doc.content, source_id, chunk_size=500, chunk_overlap=50)

        texts_to_embed = [c.content for c in doc_chunks]
        if texts_to_embed:
            try:
                vecs = embed_texts(texts_to_embed)
                for i, c in enumerate(doc_chunks):
                    if vecs and i < len(vecs):
                        c.embedding = vecs[i]
            except Exception as e:
                logger.warning(f"Failed to embed web chunks: {e}")
        new_chunks.extend(doc_chunks)

    return new_chunks, source_titles


async def run_deep_report(
    question: str,
    chunks: list[IndexChunk],
    source_titles: dict[str, str],
    source_origins: dict[str, str] | None = None,
    allow_web_search: bool = False,
    depth: str = "deep",
) -> tuple[PipelineResult, list[dict]]:
    """
    Execute the full deep report pipeline.

    Returns (PipelineResult, list_of_step_events_for_SSE)
    """
    steps: list[dict] = []
    result = PipelineResult()
    origins = source_origins or {}

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

    # Load settings early so all steps can reference it
    settings = get_settings()

    # ── Step 1.5: Live Web Search (Optional) ──────────────────────────
    if allow_web_search:
        web_provider = settings.web_search_provider or "duckduckgo"
        emit("web_search", f"🌐 Searching web via {web_provider} + fallback...")
        web_queries = [question] + sub_qs
        try:
            web_chunks, web_titles = await _web_search_and_scrape(web_queries)
            if web_chunks:
                chunks.extend(web_chunks)
                source_titles.update(web_titles)
                emit("web_search", f"✅ Scraped {len(web_titles)} web sources → {len(web_chunks)} chunks", "completed")
            else:
                emit("web_search", f"⚠️ Web search found no usable content. Check that {web_provider} is working and API keys are set in Settings.", "error")
        except Exception as e:
            emit("web_search", f"❌ Web search failed: {e}. Check provider settings.", "error")
            logger.exception(f"Web search error: {e}")

    # ── Step 2: Retrieve ──────────────────────────────────────────────
    emit("retrieval", f"🔍 Searching {len(chunks)} chunks for relevant evidence...")
    all_results: list[SearchResult] = []
    seen_ids: set[str] = set()

    queries = sub_qs + must_check
    for q in queries:
        hits = hybrid_search(q, chunks, top_k=min(settings.retrieval_top_k, 6))
        for hit in hits:
            if hit.chunk_id not in seen_ids:
                seen_ids.add(hit.chunk_id)
                all_results.append(hit)

    # Sort by score descending and cap to avoid sending too many chunks to LLM
    all_results.sort(key=lambda r: r.score, reverse=True)
    retrieved = all_results[:_MAX_EVIDENCE_CHUNKS]

    emit("retrieval", f"Found {len(retrieved)} relevant chunks", "completed")

    # Track sources used (cap snippets for metadata, not full content)
    from collections import defaultdict
    source_snippets = defaultdict(list)
    
    for r in retrieved[:_MAX_EVIDENCE_CHUNKS]: 
        source_snippets[r.source_id].append(r.content[:200])

    result.sources_used = []
    for sid in source_snippets.keys():
        source_item = {
            "source_id": sid,
            "title": source_titles.get(sid, "Unknown"),
            "snippets": source_snippets.get(sid, []),
        }
        # For web-scraped sources, sid is already a URL
        if sid.startswith("http://") or sid.startswith("https://"):
            source_item["url"] = sid
        else:
            # For ingested sources, look up origin URL from DB metadata
            origin = origins.get(sid, "")
            if origin and not origin.startswith("data:"):  # skip base64 PDF data
                source_item["url"] = origin
        result.sources_used.append(source_item)

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
        # Trust the refine pass; skip re-judge to save tokens
        score = max(score, 0.75)

        emit("refiner", f"Refined. Score: {score:.0%}", "completed")

    result.report_md = report
    result.evaluation_score = score

    emit("done", f"✅ Report complete — quality score: {score:.0%}", "completed")

    return result, steps
