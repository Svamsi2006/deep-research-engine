"""Node 3 — Clean: chunk scraped content, parse PDFs, extract repo docs."""

from __future__ import annotations

import logging
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import get_settings
from app.graph.models import (
    Chunk,
    NodeName,
    ScrapedDocument,
    RepoInfo,
    ThoughtEvent,
    UrlCategory,
)
from app.graph.state import OracleState
from app.tools.evaluator import store_chunks
from app.tools.pdf_tool import parse_pdf_to_chunks

logger = logging.getLogger(__name__)


def _collection_name(query: str) -> str:
    """Derive a ChromaDB collection name from the query."""
    slug = query.lower().replace(" ", "_")[:40]
    # ChromaDB requires [a-zA-Z0-9_-] and 3-63 chars
    safe = "".join(c for c in slug if c.isalnum() or c in "_-")
    return f"oracle_{safe}" if len(safe) >= 3 else f"oracle_{uuid.uuid4().hex[:8]}"


def clean_node(state: OracleState) -> dict:
    """
    Process all harvested content into embeddable chunks:
      1. Scraped HTML → RecursiveCharacterTextSplitter
      2. PDF stubs → PyMuPDF4LLM → chunks
      3. Repo READMEs + key files → chunks
    Store everything in ChromaDB for retrieval.
    """
    settings = get_settings()
    thoughts: list[ThoughtEvent] = []
    all_chunks: list[Chunk] = []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
    )

    # ── 1. Scraped web docs ───────────────────────────────────────────
    docs: list[ScrapedDocument] = state.get("scraped_docs", [])
    web_docs = [d for d in docs if d.content_type != UrlCategory.PDF and d.content]
    pdf_docs = [d for d in docs if d.content_type == UrlCategory.PDF]

    if web_docs:
        thoughts.append(
            ThoughtEvent(
                node=NodeName.CLEAN,
                message=f"Chunking {len(web_docs)} web documents...",
                status="running",
            )
        )
        for doc in web_docs:
            texts = splitter.split_text(doc.content)
            for i, t in enumerate(texts):
                all_chunks.append(
                    Chunk(
                        content=t,
                        source_url=doc.url,
                        source_type=UrlCategory.DOC,
                        metadata={"title": doc.title, "chunk_index": i},
                    )
                )
        thoughts.append(
            ThoughtEvent(
                node=NodeName.CLEAN,
                message=f"Created {sum(1 for c in all_chunks if c.source_type == UrlCategory.DOC)} chunks from web docs",
                status="completed",
            )
        )

    # ── 2. PDFs via PyMuPDF4LLM ──────────────────────────────────────
    if pdf_docs:
        thoughts.append(
            ThoughtEvent(
                node=NodeName.CLEAN,
                message=f"Extracting content from {len(pdf_docs)} PDFs with PyMuPDF4LLM...",
                status="running",
            )
        )
        for doc in pdf_docs:
            chunks = parse_pdf_to_chunks(doc.url, chunk_size=settings.chunk_size)
            all_chunks.extend(chunks)

        pdf_chunk_count = sum(1 for c in all_chunks if c.source_type == UrlCategory.PDF)
        thoughts.append(
            ThoughtEvent(
                node=NodeName.CLEAN,
                message=f"Extracted {pdf_chunk_count} chunks from PDFs (tables + text)",
                status="completed",
            )
        )

    # ── 3. Repo content ──────────────────────────────────────────────
    repos: list[RepoInfo] = state.get("cloned_repos", [])
    if repos:
        thoughts.append(
            ThoughtEvent(
                node=NodeName.CLEAN,
                message=f"Processing {len(repos)} cloned repositories...",
                status="running",
            )
        )
        for repo in repos:
            # README as one chunk
            if repo.readme:
                readme_texts = splitter.split_text(repo.readme)
                for i, t in enumerate(readme_texts):
                    all_chunks.append(
                        Chunk(
                            content=t,
                            source_url=repo.url,
                            source_type=UrlCategory.GITHUB,
                            metadata={"repo": repo.name, "file": "README.md", "chunk_index": i},
                        )
                    )
            # Key source files
            for path, content in repo.key_files.items():
                if path.lower().startswith("readme"):
                    continue  # Already handled
                file_texts = splitter.split_text(content)
                for i, t in enumerate(file_texts):
                    all_chunks.append(
                        Chunk(
                            content=t,
                            source_url=repo.url,
                            source_type=UrlCategory.GITHUB,
                            metadata={"repo": repo.name, "file": path, "chunk_index": i},
                        )
                    )

        repo_chunk_count = sum(1 for c in all_chunks if c.source_type == UrlCategory.GITHUB)
        thoughts.append(
            ThoughtEvent(
                node=NodeName.CLEAN,
                message=f"Created {repo_chunk_count} chunks from repos",
                status="completed",
            )
        )

    # ── Store in ChromaDB ─────────────────────────────────────────────
    if all_chunks:
        collection_name = _collection_name(state["query"])
        thoughts.append(
            ThoughtEvent(
                node=NodeName.CLEAN,
                message=f"Storing {len(all_chunks)} total chunks in ChromaDB collection '{collection_name}'",
                status="running",
            )
        )
        try:
            store_chunks(collection_name, all_chunks)
            thoughts.append(
                ThoughtEvent(
                    node=NodeName.CLEAN,
                    message="Chunks stored successfully — ready for retrieval",
                    status="completed",
                )
            )
        except Exception as e:
            logger.error(f"Failed to store chunks: {e}")
            thoughts.append(
                ThoughtEvent(
                    node=NodeName.CLEAN,
                    message=f"ChromaDB storage failed: {e}. Continuing with in-memory chunks.",
                    status="error",
                )
            )

    logger.info(f"Clean complete: {len(all_chunks)} total chunks")

    return {
        "cleaned_chunks": all_chunks,
        "thought_trace": thoughts,
        "active_node": NodeName.CLEAN.value,
    }
