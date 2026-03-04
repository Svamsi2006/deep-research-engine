"""Data Access Layer — encapsulates all SQLAlchemy DB interactions."""

from __future__ import annotations

import json
from typing import Optional

from sqlalchemy import select, update
from app.database import Source, ChunkRow, ReportRow, get_session_factory
from app.tools.indexer import IndexChunk
from app.tools.embedder import embedding_from_json


async def get_source_titles_and_chunks(
    source_ids: list[str],
) -> tuple[list[IndexChunk], dict[str, str], dict[str, str]]:
    """Retrieve chunks (with embeddings), source titles, and origin URLs.

    Returns:
        (chunks, titles_dict, origins_dict)
        origins_dict maps source_id → original URL/filename.
    """
    chunks: list[IndexChunk] = []
    titles: dict[str, str] = {}
    origins: dict[str, str] = {}

    if not source_ids:
        return chunks, titles, origins

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Load sources
        stmt = select(Source).where(Source.id.in_(source_ids))
        result = await session.execute(stmt)
        sources = result.scalars().all()
        for s in sources:
            titles[s.id] = s.title
            origins[s.id] = s.origin or ""

        # Load chunks (with stored embeddings)
        stmt = select(ChunkRow).where(ChunkRow.source_id.in_(source_ids))
        result = await session.execute(stmt)
        for c in result.scalars().all():
            chunks.append(IndexChunk(
                id=c.id,
                source_id=c.source_id,
                content=c.content,
                chunk_index=c.chunk_index,
                section_heading=c.section_heading,
                embedding=embedding_from_json(c.embedding),
            ))

    return chunks, titles, origins


async def save_report(
    report_id: str, 
    question: str, 
    report_md: str, 
    evaluation_score: float, 
    sources_used: list[dict], 
    pipeline_log: list[dict]
) -> None:
    """Save a fully generated Deep Report."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        row = ReportRow(
            id=report_id,
            question=question,
            report_md=report_md,
            evaluation_score=evaluation_score,
        )
        row.sources_used = sources_used
        row.pipeline_log = pipeline_log
        session.add(row)
        await session.commit()


async def get_report_by_id(report_id: str) -> Optional[ReportRow]:
    """Retrieve a report row by ID."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = select(ReportRow).where(ReportRow.id == report_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def update_report_flashcards(report_id: str, flashcards_json: list[dict]) -> None:
    """Update an existing report with its flashcards."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        stmt = update(ReportRow).where(ReportRow.id == report_id).values(
            flashcards_json=json.dumps(flashcards_json)
        )
        await session.execute(stmt)
        await session.commit()


async def save_ingested_source_with_chunks(
    source_id: str,
    source_type: str,
    payload: str,
    title: str,
    text: str,
    chunks: list[IndexChunk],
    chunk_embeddings: list[str | None]
) -> None:
    """Save a newly ingested source and its chunks to the database."""
    session_factory = get_session_factory()
    async with session_factory() as session:
        source = Source(
            id=source_id,
            source_type=source_type,
            origin=payload[:500] if source_type == "pdf" else payload,
            title=title,
            raw_text=text,
            char_count=len(text),
        )
        session.add(source)

        for i, chunk in enumerate(chunks):
            row = ChunkRow(
                id=chunk.id,
                source_id=source_id,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                section_heading=chunk.section_heading,
                char_count=len(chunk.content),
                embedding=chunk_embeddings[i],
            )
            session.add(row)

        await session.commit()
