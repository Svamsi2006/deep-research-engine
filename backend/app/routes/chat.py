"""Chat & Report routes — SSE streaming endpoints for Answer, Deep Report, and Flashcards."""

from __future__ import annotations

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


async def _load_chunks(source_ids: list[str]) -> tuple[list[IndexChunk], dict[str, str]]:
    """Load chunks and source titles from DB for given source_ids."""
    chunks: list[IndexChunk] = []
    titles: dict[str, str] = {}

    if not source_ids:
        return chunks, titles

    session_factory = get_session_factory()
    async with session_factory() as session:
        from sqlalchemy import select

        # Load sources
        stmt = select(Source).where(Source.id.in_(source_ids))
        result = await session.execute(stmt)
        sources = result.scalars().all()
        for s in sources:
            titles[s.id] = s.title

        # Load chunks
        stmt = select(ChunkRow).where(ChunkRow.source_id.in_(source_ids))
        result = await session.execute(stmt)
        for c in result.scalars().all():
            chunks.append(IndexChunk(
                id=c.id,
                source_id=c.source_id,
                content=c.content,
                chunk_index=c.chunk_index,
                section_heading=c.section_heading,
            ))

    return chunks, titles


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


@router.post("/api/answer")
async def answer(request: AnswerRequest):
    """Quick answer — direct LLM call, optionally with source context."""
    settings = get_settings()
    if not settings.openrouter_api_key and not settings.groq_api_key:
        raise HTTPException(status_code=500, detail="No LLM API key configured")

    report_id = str(uuid.uuid4())

    async def stream():
        yield _thought("answer", f"⚡ Generating quick answer...", "running")

        # Load source context if provided
        context = ""
        if request.source_ids:
            chunks, titles = await _load_chunks(request.source_ids)
            if chunks:
                context = "\n\n---\n\n".join(
                    f"[{c.section_heading}] {c.content[:500]}" for c in chunks[:10]
                )
                context = f"\n\nContext from your sources:\n{context}"

        try:
            messages = [
                {"role": "system", "content": ANSWER_SYSTEM},
                {"role": "user", "content": request.question + context},
            ]
            result = call_llm(messages, purpose="answer", max_tokens=2048, temperature=0.5)

            yield _thought("answer", f"✅ Response ready ({len(result.text)} chars, via {result.provider})", "completed")

            # Stream as report chunks
            text = result.text
            chunk_size = 200
            for i in range(0, len(text), chunk_size):
                yield _sse("report", {
                    "content": text[i:i + chunk_size],
                    "done": i + chunk_size >= len(text),
                })

        except Exception as e:
            logger.error(f"Answer failed: {e}")
            yield _sse("error", {"message": str(e), "node": "answer"})

        yield _done(report_id)

    return EventSourceResponse(stream())


# ---------------------------------------------------------------------------
# POST /api/report — Deep Report Pipeline
# ---------------------------------------------------------------------------


@router.post("/api/report")
async def report(request: ReportRequest):
    """Deep report — runs full Planner→Retrieve→Write→Judge→Refine pipeline."""
    settings = get_settings()
    if not settings.openrouter_api_key and not settings.groq_api_key:
        raise HTTPException(status_code=500, detail="No LLM API key configured")

    report_id = str(uuid.uuid4())

    async def stream():
        yield _thought("system", f"🧠 Starting deep report pipeline: \"{request.question}\"", "running")

        # Load chunks from ingested sources
        chunks, titles = await _load_chunks(request.source_ids)

        yield _thought("system", f"📦 Loaded {len(chunks)} chunks from {len(titles)} sources", "completed")

        try:
            # Run the pipeline (synchronous, but streams steps)
            result, step_events = run_deep_report(
                question=request.question,
                chunks=chunks,
                source_titles=titles,
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
                session_factory = get_session_factory()
                async with session_factory() as session:
                    row = ReportRow(
                        id=report_id,
                        question=request.question,
                        report_md=result.report_md,
                        evaluation_score=result.evaluation_score,
                    )
                    row.sources_used = result.sources_used
                    row.pipeline_log = step_events
                    session.add(row)
                    await session.commit()
            except Exception as e:
                logger.warning(f"Failed to persist report: {e}")

            yield _done(report_id, score=result.evaluation_score)

        except Exception as e:
            logger.exception(f"Pipeline error: {e}")
            yield _sse("error", {"message": str(e), "node": "pipeline"})
            yield _done(report_id, score=0.0)

    return EventSourceResponse(stream())


# ---------------------------------------------------------------------------
# POST /api/flashcards — Generate flashcards from report
# ---------------------------------------------------------------------------


@router.post("/api/flashcards")
async def flashcards(request: FlashcardRequest):
    """Generate flashcards from a report."""
    settings = get_settings()
    if not settings.openrouter_api_key and not settings.groq_api_key:
        raise HTTPException(status_code=500, detail="No LLM API key configured")

    # Get report content
    report_md = request.report_md or ""

    if not report_md and request.report_id:
        try:
            session_factory = get_session_factory()
            async with session_factory() as session:
                from sqlalchemy import select
                stmt = select(ReportRow).where(ReportRow.id == request.report_id)
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
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
                session_factory = get_session_factory()
                async with session_factory() as session:
                    from sqlalchemy import select, update
                    stmt = update(ReportRow).where(ReportRow.id == report_id).values(
                        flashcards_json=json.dumps(cards_json)
                    )
                    await session.execute(stmt)
                    await session.commit()
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Flashcard generation failed: {e}")
            yield _sse("error", {"message": str(e), "node": "flashcards"})

        yield _done(report_id)

    return EventSourceResponse(stream())
