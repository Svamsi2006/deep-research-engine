"""Ingest route — accepts PDFs, URLs, and GitHub links, extracts text, stores as sources."""

from __future__ import annotations

import base64
import logging
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.database import Source, ChunkRow, get_session_factory
from app.tools.indexer import chunk_text

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------


class IngestRequest(BaseModel):
    source_type: str              # "pdf", "url", "github"
    payload: str                  # URL string, or base64 PDF
    file_name: Optional[str] = None


class IngestResponse(BaseModel):
    source_id: str
    title: str
    char_count: int
    chunk_count: int


# ---------------------------------------------------------------------------
# Extractors
# ---------------------------------------------------------------------------


def _extract_pdf(payload: str, file_name: str) -> tuple[str, str]:
    """Extract text from base64-encoded PDF. Returns (title, text)."""
    try:
        pdf_bytes = base64.b64decode(payload)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid base64 PDF: {e}")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", prefix="ingest_")
    tmp.write(pdf_bytes)
    tmp.close()

    try:
        from app.tools.pdf_tool import parse_pdf
        text = parse_pdf(tmp.name)
        if not text:
            raise HTTPException(status_code=422, detail="Could not extract text from PDF")
        return (file_name or "Uploaded PDF", text)
    finally:
        try:
            Path(tmp.name).unlink()
        except OSError:
            pass


def _extract_url(url: str) -> tuple[str, str]:
    """Extract text from a web URL. Returns (title, text)."""
    from app.tools.scraper import scrape_url
    try:
        result = scrape_url(url)
        title = result.get("title", url) if isinstance(result, dict) else url
        text = result.get("content", "") if isinstance(result, dict) else str(result)
        if not text:
            raise HTTPException(status_code=422, detail=f"Could not extract content from {url}")
        return (title, text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to scrape URL: {e}")


def _extract_github(url: str) -> tuple[str, str]:
    """Extract README + key files from a GitHub repo URL. Returns (title, text)."""
    from app.tools.git_tool import clone_and_extract
    try:
        result = clone_and_extract(url)
        title = result.get("repo_name", url) if isinstance(result, dict) else url
        text = result.get("content", "") if isinstance(result, dict) else str(result)
        if not text:
            raise HTTPException(status_code=422, detail=f"Could not extract content from GitHub: {url}")
        return (title, text)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to process GitHub URL: {e}")


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post("/api/ingest", response_model=IngestResponse)
async def ingest(request: IngestRequest):
    """
    Ingest a source document (PDF, URL, or GitHub link).

    Extracts text, chunks it, and stores both in the database.
    Returns source_id for later use in report generation.
    """
    source_id = str(uuid.uuid4())

    # ── Extract text based on type ────────────────────────────────────
    if request.source_type == "pdf":
        title, text = _extract_pdf(request.payload, request.file_name or "document.pdf")
    elif request.source_type == "url":
        title, text = _extract_url(request.payload)
    elif request.source_type == "github":
        title, text = _extract_github(request.payload)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown source_type: {request.source_type}")

    # ── Chunk the text ────────────────────────────────────────────────
    from app.config import get_settings
    settings = get_settings()

    chunks = chunk_text(
        text,
        source_id=source_id,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    # ── Store in database ─────────────────────────────────────────────
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            # Store source
            source = Source(
                id=source_id,
                source_type=request.source_type,
                origin=request.payload[:500] if request.source_type == "pdf" else request.payload,
                title=title,
                raw_text=text,
                char_count=len(text),
            )
            session.add(source)

            # Store chunks
            for chunk in chunks:
                row = ChunkRow(
                    id=chunk.id,
                    source_id=source_id,
                    content=chunk.content,
                    chunk_index=chunk.chunk_index,
                    section_heading=chunk.section_heading,
                    char_count=len(chunk.content),
                )
                session.add(row)

            await session.commit()
    except Exception as e:
        logger.error(f"Failed to store source: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    logger.info(f"Ingested {request.source_type}: {title} → {len(chunks)} chunks")

    return IngestResponse(
        source_id=source_id,
        title=title,
        char_count=len(text),
        chunk_count=len(chunks),
    )
