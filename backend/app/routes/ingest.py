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
        if not text or not text.strip():
            raise HTTPException(
                status_code=422,
                detail="PDF appears to be an image or scanned document. OCR is required, please provide a text-searchable PDF."
            )
        return (file_name or "Uploaded PDF", text)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    finally:
        try:
            Path(tmp.name).unlink()
        except OSError:
            pass


async def _extract_url(url: str) -> tuple[str, str]:
    """Extract text from a web URL. Returns (title, text)."""
    from app.tools.scraper import scrape_urls, scrape_url_metadata_fallback
    try:
        docs = await scrape_urls([url], max_concurrent=1)
        if not docs:
            logger.warning(f"Full scrape blocked/empty for {url}, trying metadata fallback")
            try:
                meta = scrape_url_metadata_fallback(url)
                return (meta["title"], meta["content"])
            except Exception as meta_err:
                logger.warning(f"Metadata fallback failed for {url}: {meta_err}")

                from app.tools.search import duckduckgo_search

                snippets = duckduckgo_search(url, max_results=3)
                if snippets:
                    top = snippets[0]
                    title = top.get("title") or url
                    snippet_text = top.get("snippet") or ""
                    content = (
                        f"Title: {title}\n"
                        f"URL: {top.get('url', url)}\n"
                        f"Summary (from web index): {snippet_text}"
                    )
                    return (title, content)

            raise HTTPException(status_code=422, detail=f"Could not extract content from {url} (site may block scrapers and metadata fetch failed)")
        return (docs[0].title, docs[0].content)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to scrape URL: {e}")


def _extract_github(url: str) -> tuple[str, str]:
    """Extract README + key files from a GitHub repo URL. Returns (title, text)."""
    from app.tools.git_tool import clone_and_parse_repo
    try:
        result = clone_and_parse_repo(url)
        title = result.name or url
        # Combine readme + key file contents
        parts = []
        if result.readme:
            parts.append(result.readme)
        for path, content in result.key_files.items():
            if path.lower() not in ("readme.md", "readme.rst"):
                parts.append(f"--- {path} ---\n{content}")
        text = "\n\n".join(parts)
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


@router.post("/ingest", response_model=IngestResponse)
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
        title, text = await _extract_url(request.payload)
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

    # ── Compute embeddings (batch) ────────────────────────────────────
    chunk_embeddings: list[str | None] = [None] * len(chunks)
    pinecone_vectors = []
    
    if chunks:
        try:
            from app.tools.embedder import embed_texts, embedding_to_json
            texts_to_embed = [c.content for c in chunks]
            embedding_vecs = embed_texts(texts_to_embed)
            if embedding_vecs is not None:
                chunk_embeddings = [embedding_to_json(v) for v in embedding_vecs]
                
                # Prepare Pinecone vectors
                pinecone_vectors = [
                    {
                        "id": c.id,
                        "values": vec,
                        "metadata": {
                            "source_id": source_id,
                            "title": title,
                            "section": c.section_heading,
                            "type": request.source_type,
                        }
                    }
                    for c, vec in zip(chunks, embedding_vecs)
                ]
                logger.info(f"Embedded {len(embedding_vecs)} chunks for source {source_id}")
        except Exception as e:
            logger.warning(f"Embedding computation failed — storing without embeddings: {e}")

    # ── Store in database ─────────────────────────────────────────────
    try:
        from app.dal import save_ingested_source_with_chunks
        await save_ingested_source_with_chunks(
            source_id=source_id,
            source_type=request.source_type,
            payload=request.payload,
            title=title,
            text=text,
            chunks=chunks,
            chunk_embeddings=chunk_embeddings
        )
    except Exception as e:
        logger.error(f"Failed to store source: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    # ── Store embeddings in Pinecone ──────────────────────────────────
    if pinecone_vectors:
        try:
            from app.tools.pinecone_client import upsert_embeddings
            await upsert_embeddings(pinecone_vectors, namespace=request.source_type)
            logger.info(f"Stored {len(pinecone_vectors)} embeddings in Pinecone")
        except Exception as e:
            logger.warning(f"Pinecone storage failed: {e} — document indexed in DB only")

    logger.info(f"Ingested {request.source_type}: {title} → {len(chunks)} chunks")

    return IngestResponse(
        source_id=source_id,
        title=title,
        char_count=len(text),
        chunk_count=len(chunks),
    )
