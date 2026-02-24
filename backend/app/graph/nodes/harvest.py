"""Node 2 — Harvest: parallel scraping of docs + cloning GitHub repos + PDF download."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging


def _run_async(coro):
    """Run an async coroutine safely even when an event loop is already running.

    Spawns a fresh thread (no running loop) and uses asyncio.run() there,
    blocking the calling thread until the result is ready.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(asyncio.run, coro)
        return future.result()

from app.graph.models import (
    NodeName,
    ScrapedDocument,
    RepoInfo,
    SearchResult,
    ThoughtEvent,
    UrlCategory,
)
from app.graph.state import OracleState
from app.tools.git_tool import clone_and_parse_repo
from app.tools.scraper import classify_url, scrape_urls

logger = logging.getLogger(__name__)


def harvest_node(state: OracleState) -> dict:
    """
    Partition discovered URLs by type and harvest in parallel:
      - Doc URLs → web scrape
      - GitHub URLs → shallow clone via GitPython
      - PDF URLs → download (scraped as binary, parsed in Clean node)
    """
    results: list[SearchResult] = state.get("search_results", [])
    thoughts: list[ThoughtEvent] = []

    # ── Partition URLs ────────────────────────────────────────────────
    doc_urls: list[str] = []
    github_urls: list[str] = []
    pdf_urls: list[str] = []

    for r in results:
        cat = classify_url(r.url)
        if cat == UrlCategory.GITHUB:
            github_urls.append(r.url)
        elif cat == UrlCategory.PDF:
            pdf_urls.append(r.url)
        else:
            doc_urls.append(r.url)

    thoughts.append(
        ThoughtEvent(
            node=NodeName.HARVEST,
            message=(
                f"Partitioned {len(results)} URLs: "
                f"{len(doc_urls)} docs, {len(github_urls)} repos, {len(pdf_urls)} PDFs"
            ),
            status="running",
        )
    )

    # ── Scrape docs (async) ───────────────────────────────────────────
    scraped_docs: list[ScrapedDocument] = []
    if doc_urls:
        thoughts.append(
            ThoughtEvent(
                node=NodeName.HARVEST,
                message=f"Scraping {len(doc_urls)} web pages...",
                status="running",
            )
        )
        try:
            scraped_docs = _run_async(scrape_urls(doc_urls))
        except Exception as e:
            logger.warning(f"Scraping failed: {e}")
            scraped_docs = []

        thoughts.append(
            ThoughtEvent(
                node=NodeName.HARVEST,
                message=f"Scraped {len(scraped_docs)} pages successfully",
                status="completed",
            )
        )

    # ── Also add PDF URLs as ScrapedDocument stubs (parsed in Clean) ─
    for url in pdf_urls:
        scraped_docs.append(
            ScrapedDocument(
                url=url,
                title="",
                content="",  # Content extracted in Clean node via PyMuPDF4LLM
                content_type=UrlCategory.PDF,
            )
        )

    if pdf_urls:
        thoughts.append(
            ThoughtEvent(
                node=NodeName.HARVEST,
                message=f"Queued {len(pdf_urls)} PDFs for extraction in Clean node",
                status="completed",
            )
        )

    # ── Clone repos ───────────────────────────────────────────────────
    cloned_repos: list[RepoInfo] = []
    for url in github_urls[:3]:  # Cap at 3 repos to avoid long waits
        # Normalise to clone-able URL
        clone_url = url.rstrip("/")
        if not clone_url.endswith(".git"):
            # Only clone repo roots, not file paths
            parts = clone_url.replace("https://github.com/", "").split("/")
            if len(parts) >= 2:
                clone_url = f"https://github.com/{parts[0]}/{parts[1]}.git"
            else:
                continue

        thoughts.append(
            ThoughtEvent(
                node=NodeName.HARVEST,
                message=f"Cloning repo: {clone_url}",
                status="running",
            )
        )

        repo_info = clone_and_parse_repo(clone_url)
        if repo_info.readme or repo_info.key_files:
            cloned_repos.append(repo_info)
            thoughts.append(
                ThoughtEvent(
                    node=NodeName.HARVEST,
                    message=f"Cloned {repo_info.name}: {len(repo_info.key_files)} key files, {len(repo_info.file_tree)} total files",
                    status="completed",
                )
            )
        else:
            thoughts.append(
                ThoughtEvent(
                    node=NodeName.HARVEST,
                    message=f"Repo {clone_url} yielded no content — skipped",
                    status="completed",
                )
            )

    logger.info(
        f"Harvest complete: {len(scraped_docs)} docs, {len(cloned_repos)} repos"
    )

    return {
        "scraped_docs": scraped_docs,
        "cloned_repos": cloned_repos,
        "thought_trace": thoughts,
        "active_node": NodeName.HARVEST.value,
    }
