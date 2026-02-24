"""PDF parsing tool — PyMuPDF4LLM for structured PDF → Markdown conversion."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import httpx
from langchain_core.tools import tool

from app.graph.models import Chunk, UrlCategory

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _download_pdf(url: str) -> Path:
    """Download a PDF from a URL into a temp file and return its path."""
    resp = httpx.get(
        url,
        follow_redirects=True,
        timeout=30.0,
        headers={
            "User-Agent": "Mozilla/5.0 (engineering-oracle/1.0)"
        },
    )
    resp.raise_for_status()

    suffix = ".pdf"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="oracle_pdf_")
    tmp.write(resp.content)
    tmp.close()
    return Path(tmp.name)


def _pdf_to_markdown(pdf_path: str | Path) -> str:
    """
    Convert a PDF to Markdown using PyMuPDF4LLM.

    Handles multi-column layouts and tables automatically via PyMuPDF4LLM's
    built-in heuristics.
    """
    import pymupdf4llm

    md_text = pymupdf4llm.to_markdown(
        str(pdf_path),
        write_images=False,    # Skip image extraction to keep output lean
        show_progress=False,
    )
    return md_text


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def parse_pdf(source: str) -> str:
    """
    Parse a PDF from a local path or URL → Markdown string.

    Args:
        source: Either a local file path or an HTTP(S) URL pointing to a PDF.

    Returns:
        Markdown text extracted from the PDF.
    """
    path: Path | None = None
    is_temp = False

    try:
        if source.startswith(("http://", "https://")):
            path = _download_pdf(source)
            is_temp = True
        else:
            path = Path(source)
            if not path.exists():
                logger.error(f"PDF not found: {source}")
                return ""

        md = _pdf_to_markdown(path)
        logger.info(f"Parsed PDF {source} → {len(md)} chars of Markdown")
        return md

    except Exception as e:
        logger.error(f"Failed to parse PDF {source}: {e}")
        return ""
    finally:
        if is_temp and path and path.exists():
            try:
                path.unlink()
            except OSError:
                pass


def parse_pdf_to_chunks(source: str, chunk_size: int = 2000) -> list[Chunk]:
    """Parse a PDF and split into chunks suitable for embedding."""
    md = parse_pdf(source)
    if not md:
        return []

    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=200,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
    )
    texts = splitter.split_text(md)

    return [
        Chunk(
            content=t,
            source_url=source,
            source_type=UrlCategory.PDF,
            metadata={"chunk_index": i},
        )
        for i, t in enumerate(texts)
    ]


@tool
def parse_pdf_tool(source: str) -> str:
    """Parse a PDF (URL or local path) into structured Markdown text."""
    return parse_pdf(source)
