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
    try:
        import pymupdf4llm

        md_text = pymupdf4llm.to_markdown(
            str(pdf_path),
            write_images=False,    # Skip image extraction to keep output lean
            show_progress=False,
        )
        if md_text and md_text.strip():
            return md_text
    except Exception as e:
        logger.warning(f"pymupdf4llm unavailable/failed, falling back to basic fitz: {e}")

    # Fallback to pure local extraction if empty or errored
    try:
        import fitz  # PyMuPDF fallback
        logger.info(f"Using fitz fallback for {pdf_path}")
        doc = fitz.open(str(pdf_path))
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        logger.error(f"Fallback extraction failed: {e}")
        return ""


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

def parse_pdf(source: str) -> str:
    """
    Parse a PDF from a local path or URL → Markdown string.
    
    Raises ValueError if PDF is image-based (scanned) with insufficient text.
    """
    # Download if URL
    if source.startswith("http"):
        pdf_path = _download_pdf(source)
    else:
        pdf_path = Path(source)

    try:
        md = _pdf_to_markdown(pdf_path)
        
        # Check if it's a scanned PDF (very little text)
        if md and len(md.strip()) > 100:
            return md
        
        # Fallback: try direct PyMuPDF extraction
        import fitz
        doc = fitz.open(str(pdf_path))
        if len(doc) == 0:
            raise ValueError("PDF is empty")
        
        text = ""
        for page in doc:
            text += page.get_text()
        
        if len(text.strip()) < 50:
            raise ValueError(
                "PDF appears to be an image or scanned document with no extractable text. "
                "OCR is required to process this PDF. Please provide a text-based PDF."
            )
        
        logger.info(f"Extracted {len(text)} chars from PDF using fallback")
        return text
    except ValueError:
        raise
    except Exception as e:
        logger.error(f"PDF parsing failed: {e}")
        raise ValueError(f"Failed to parse PDF: {e}")
    finally:
        # Cleanup temp file
        if isinstance(pdf_path, Path) and pdf_path.name.startswith("oracle_pdf_"):
            try:
                pdf_path.unlink()
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
