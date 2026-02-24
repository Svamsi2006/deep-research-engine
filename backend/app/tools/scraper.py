"""Web scraping tool — httpx + BeautifulSoup with rate-limit resilience."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from langchain_core.tools import tool
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.graph.models import ScrapedDocument, UrlCategory

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# URL classification
# ---------------------------------------------------------------------------

def classify_url(url: str) -> UrlCategory:
    """Classify a URL into doc / github / pdf / other."""
    parsed = urlparse(url)
    if url.lower().endswith(".pdf"):
        return UrlCategory.PDF
    if "github.com" in parsed.netloc:
        return UrlCategory.GITHUB
    if any(
        d in parsed.netloc
        for d in ["arxiv.org", "docs.", "readthedocs", "wiki", "medium.com", "blog"]
    ):
        return UrlCategory.DOC
    return UrlCategory.OTHER


# ---------------------------------------------------------------------------
# Single-page scraper with retries
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


class ScrapingBlockedError(Exception):
    """Raised when a site returns 403 / Cloudflare challenge."""


class RateLimitError(Exception):
    """Raised on HTTP 429."""


@retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def _fetch_page(client: httpx.AsyncClient, url: str) -> str:
    """Fetch a single URL with retry on 429."""
    resp = await client.get(url, headers=HEADERS, follow_redirects=True, timeout=20.0)
    if resp.status_code == 429:
        raise RateLimitError(f"Rate limited on {url}")
    if resp.status_code == 403:
        raise ScrapingBlockedError(f"Blocked (403) on {url}")
    resp.raise_for_status()
    return resp.text


def _extract_text(html: str, url: str) -> tuple[str, str]:
    """Extract clean text + title from HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""

    # Try <article> or <main> first for higher-quality content
    main = soup.find("article") or soup.find("main") or soup.find("div", {"role": "main"})
    if main:
        text = main.get_text(separator="\n", strip=True)
    else:
        text = soup.body.get_text(separator="\n", strip=True) if soup.body else soup.get_text(
            separator="\n", strip=True
        )

    # Collapse blank lines
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    text = "\n".join(lines)
    return title, text


# ---------------------------------------------------------------------------
# Public: parallel batch scraper
# ---------------------------------------------------------------------------

async def scrape_urls(urls: list[str], max_concurrent: int = 5) -> list[ScrapedDocument]:
    """
    Scrape multiple URLs in parallel.

    Skips URLs that are blocked or error out — never crashes the pipeline.
    """
    settings = get_settings()
    sem = asyncio.Semaphore(max_concurrent)
    results: list[ScrapedDocument] = []

    async def _scrape_one(client: httpx.AsyncClient, url: str) -> Optional[ScrapedDocument]:
        async with sem:
            try:
                html = await _fetch_page(client, url)
                title, text = _extract_text(html, url)
                if len(text) < 50:
                    logger.info(f"Skipping {url} — too little content ({len(text)} chars)")
                    return None
                return ScrapedDocument(
                    url=url,
                    title=title,
                    content=text[:50_000],  # cap at 50k chars
                    content_type=classify_url(url),
                )
            except ScrapingBlockedError:
                logger.warning(f"Scraping blocked for {url} — skipping")
                return None
            except RateLimitError:
                logger.warning(f"Rate-limited after retries on {url} — skipping")
                return None
            except Exception as e:
                logger.warning(f"Failed to scrape {url}: {e}")
                return None

    async with httpx.AsyncClient() as client:
        tasks = [_scrape_one(client, url) for url in urls[: settings.max_scrape_urls]]
        docs = await asyncio.gather(*tasks)
        results = [d for d in docs if d is not None]

    logger.info(f"Scraped {len(results)}/{len(urls)} URLs successfully")
    return results


# ---------------------------------------------------------------------------
# LangChain tool wrapper (sync, for LangGraph tool nodes)
# ---------------------------------------------------------------------------

@tool
def scrape_urls_tool(urls: list[str]) -> list[dict]:
    """Scrape a list of URLs and return their text content."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, scrape_urls(urls))
        docs = future.result()
    return [d.model_dump() for d in docs]
