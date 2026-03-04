"""Chat & Report routes — SSE streaming endpoints for Answer, Deep Report, and Flashcards."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.config import get_settings
from app.database import Source, ChunkRow, ReportRow, get_session_factory
from app.llm_gateway import call_llm
from app.pipeline import run_deep_report, PipelineResult
from app.flashcards import generate_flashcards, flashcards_to_csv, flashcards_to_json

# Suppress noisy asyncio socket.send warnings (happen on normal client disconnect)
logging.getLogger("asyncio").setLevel(logging.ERROR)
from app.tools.indexer import IndexChunk

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class AnswerRequest(BaseModel):
    question: str
    source_ids: list[str] = []
    allow_web_search: bool = False


class ReportRequest(BaseModel):
    question: str
    source_ids: list[str] = []
    depth: str = "deep"  # "quick" or "deep"
    allow_web_search: bool = False


class FlashcardRequest(BaseModel):
    report_id: Optional[str] = None
    report_md: Optional[str] = None
    question: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sse(event: str, data: dict) -> dict:
    return {"event": event, "data": json.dumps(data)}


def _thought(node: str, message: str, status: str = "running") -> dict:
    return _sse("thought", {
        "node": node, "message": message, "status": status,
        "timestamp": datetime.utcnow().isoformat(),
    })


def _done(report_id: str, score: float = 1.0, **extra) -> dict:
    return _sse("done", {
        "report_id": report_id, "evaluation_score": score,
        "retry_count": 0, "quality_warning": False, **extra,
    })


def _provider_has_runtime_key(settings) -> bool:
    provider = (settings.ai_provider or "").strip().lower()
    if provider == "ollama":
        return True

    if settings.ai_api_key:
        return True

    provider_keys = {
        "openrouter": settings.openrouter_api_key,
        "groq": settings.groq_api_key,
        "openai": settings.openai_api_key,
        "gemini": settings.google_api_key,
        "deepseek": settings.deepseek_api_key,
        "grok": settings.grok_api_key,
    }
    return bool(provider_keys.get(provider, ""))


def _has_any_llm_config(settings) -> bool:
    return _provider_has_runtime_key(settings) or bool(settings.openrouter_api_key) or bool(settings.groq_api_key)


async def _load_chunks(source_ids: list[str]) -> tuple[list[IndexChunk], dict[str, str], dict[str, str]]:
    """Load chunks, source titles, and origin URLs from DB."""
    from app.dal import get_source_titles_and_chunks
    return await get_source_titles_and_chunks(source_ids)


# ---------------------------------------------------------------------------
# POST /api/answer — Quick answer (Brain Router style)
# ---------------------------------------------------------------------------

ANSWER_SYSTEM = """\
You are Engineering Oracle, a senior systems architect and ML engineer.
Provide helpful, technically accurate, and concise answers.
Use Markdown: headers, code blocks, bullet points, tables.
Do NOT output model documentation or API specs unless asked.
If the question needs deep research, suggest using "Deep Report" mode.
"""


@router.post("/answer")
async def answer(request: AnswerRequest):
    """Quick answer — direct LLM call, optionally with source context + web search."""
    settings = get_settings()
    if not _has_any_llm_config(settings):
        raise HTTPException(status_code=500, detail="No LLM API key configured")

    report_id = str(uuid.uuid4())

    async def stream():
        try:
            yield _thought("answer", f"🔍 Searching sources...", "running")

            # Load source context if provided
            context = ""
            sources_used = []
            if request.source_ids:
                chunks, titles, origins = await _load_chunks(request.source_ids)
                if chunks:
                    # Cap to 5 chunks, 300 chars each to stay within token budget
                    context = "\n\n---\n\n".join(
                        f"[{c.section_heading}] {c.content[:300]}" for c in chunks[:5]
                    )
                    context = f"\n\nContext from your sources:\n{context}"
                    sources_used = [
                        {"source_id": sid, "title": t, "url": origins.get(sid, ""), "type": "document"}
                        for sid, t in titles.items()
                    ]

            # Web search if enabled
            web_results = []
            if request.allow_web_search:
                yield _thought("answer", f"🌐 Searching web for: {request.question}", "running")
                try:
                    from app.tools.search import search_web
                    web_results = search_web(request.question, max_results=5)
                    if web_results:
                        web_snippet = "\n\n---\n\nWeb Search Results:\n"
                        for i, result in enumerate(web_results[:3], 1):
                            web_snippet += f"\n[Web {i}] {result.get('title', 'Result')}\n"
                            web_snippet += f"URL: {result.get('url', '')}\n"
                            web_snippet += f"Snippet: {result.get('snippet', '')[:300]}\n"
                        context += web_snippet
                        sources_used.extend([{"title": r.get("title"), "url": r.get("url"), "type": "web"} for r in web_results])
                except Exception as e:
                    logger.warning(f"Web search failed: {e}")

            yield _thought("answer", f"✍️  Generating answer...", "running")

            try:
                messages = [
                    {"role": "system", "content": ANSWER_SYSTEM},
                    {"role": "user", "content": request.question + context},
                ]
                result = call_llm(messages, purpose="answer", max_tokens=1500, temperature=0.5)

                yield _thought("answer", f"✅ Response ready ({len(result.text)} chars, via {result.provider})", "completed")

                # Use Perplexity-style formatting
                from app.formatting import format_answer_with_sources
                formatted = format_answer_with_sources(
                    result.text,
                    sources_used,
                    confidence=0.95,
                    search_results=web_results
                )

                # Stream answer content
                yield _sse("report", {
                    "content": formatted["answer"],
                    "done": True,
                })

                # Emit structured sources for the Sources panel
                all_sources = sources_used + [
                    {"title": r.get("title", "Web Result"), "url": r.get("url", ""), "type": "web"}
                    for r in web_results
                ]
                if all_sources:
                    yield _sse("sources", {"sources": all_sources})

            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                yield _sse("error", {"message": str(e), "node": "answer"})

        except asyncio.CancelledError:
            logger.info("Answer stream cancelled by client disconnect")
            return
        except Exception as e:
            logger.error(f"Answer stream failed: {e}")
            yield _sse("error", {"message": str(e)})

        yield _done(report_id)

    return EventSourceResponse(stream())


# ---------------------------------------------------------------------------
# POST /api/report — Deep Report Pipeline
# ---------------------------------------------------------------------------


@router.post("/report")
async def report(request: ReportRequest):
    """Deep report — runs full Planner→Retrieve→Write→Judge→Refine pipeline."""
    settings = get_settings()
    if not _has_any_llm_config(settings):
        raise HTTPException(status_code=500, detail="No LLM API key configured")

    report_id = str(uuid.uuid4())

    async def stream():
        yield _thought("system", f"🧠 Starting deep report pipeline: \"{request.question}\"", "running")

        # Load chunks from ingested sources
        chunks, titles, origins = await _load_chunks(request.source_ids)

        yield _thought("system", f"📦 Loaded {len(chunks)} chunks from {len(titles)} sources", "completed")

        try:
            # Run the pipeline (which now supports async web search)
            result, step_events = await run_deep_report(
                question=request.question,
                chunks=chunks,
                source_titles=titles,
                source_origins=origins,
                allow_web_search=request.allow_web_search,
                depth=request.depth,
            )

            # Stream all pipeline steps
            for step in step_events:
                yield _sse("thought", step)

            # Handle "need more sources"
            if result.need_more_sources:
                yield _sse("need_more_sources", {
                    "message": result.need_more_message,
                })
                yield _done(report_id, score=0.0)
                return

            # Stream report
            report_text = result.report_md
            chunk_size = 200
            for i in range(0, len(report_text), chunk_size):
                yield _sse("report", {
                    "content": report_text[i:i + chunk_size],
                    "done": i + chunk_size >= len(report_text),
                })

            # Stream sources used
            yield _sse("sources", {"sources": result.sources_used})

            # Persist
            try:
                from app.dal import save_report
                await save_report(
                    report_id=report_id,
                    question=request.question,
                    report_md=result.report_md,
                    evaluation_score=result.evaluation_score,
                    sources_used=result.sources_used,
                    pipeline_log=step_events
                )
            except Exception as e:
                logger.warning(f"Failed to persist report: {e}")

            yield _done(report_id, score=result.evaluation_score)

        except asyncio.CancelledError:
            logger.info("Report stream cancelled by client disconnect")
            return
        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            yield _sse("error", {"message": str(e), "node": "pipeline"})
            yield _done(report_id, score=0.0)

    return EventSourceResponse(stream())


# ---------------------------------------------------------------------------
# POST /api/flashcards — Generate flashcards from report
# ---------------------------------------------------------------------------


@router.post("/flashcards")
async def flashcards(request: FlashcardRequest):
    """Generate flashcards from a report."""
    settings = get_settings()
    if not _has_any_llm_config(settings):
        raise HTTPException(status_code=500, detail="No LLM API key configured")

    # Get report content
    report_md = request.report_md or ""

    if not report_md and request.report_id:
        try:
            from app.dal import get_report_by_id
            row = await get_report_by_id(request.report_id)
            if row:
                report_md = row.report_md
                if not request.question:
                    request.question = row.question
        except Exception as e:
            logger.error(f"Failed to load report: {e}")

    if not report_md:
        raise HTTPException(status_code=400, detail="No report content provided")

    report_id = request.report_id or str(uuid.uuid4())

    async def stream():
        yield _thought("flashcards", "🃏 Generating flashcards from report...", "running")

        try:
            cards = generate_flashcards(report_md, request.question)

            yield _thought("flashcards", f"✅ Generated {len(cards)} flashcards", "completed")

            # Send flashcards
            cards_json = flashcards_to_json(cards)
            cards_csv = flashcards_to_csv(cards)

            yield _sse("flashcards", {
                "cards": cards_json,
                "csv": cards_csv,
                "count": len(cards),
            })

            # Persist flashcards to report
            try:
                from app.dal import update_report_flashcards
                await update_report_flashcards(report_id, cards_json)
            except Exception:
                pass

        except asyncio.CancelledError:
            logger.info("Flashcards stream cancelled by client disconnect")
            return
        except Exception as e:
            logger.error(f"Flashcard generation failed: {e}")
            yield _sse("error", {"message": str(e), "node": "flashcards"})

        yield _done(report_id)

    return EventSourceResponse(stream())
