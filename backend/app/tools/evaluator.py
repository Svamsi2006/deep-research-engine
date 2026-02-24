"""Evaluator tool — ChromaDB + sentence-transformers for cosine similarity scoring.

Falls back gracefully if sentence-transformers or ChromaDB are unavailable.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings
from app.graph.models import Chunk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional dependency imports
# ---------------------------------------------------------------------------

_HAS_SENTENCE_TRANSFORMERS = False
_SentenceTransformerEmbeddingFunction = None

try:
    import chromadb
    from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
    _SentenceTransformerEmbeddingFunction = SentenceTransformerEmbeddingFunction
    _HAS_SENTENCE_TRANSFORMERS = True
except Exception as e:
    logger.warning(f"ChromaDB/sentence-transformers not available: {e}")
    chromadb = None  # type: ignore


# ---------------------------------------------------------------------------
# Singleton-ish clients (initialized once at app startup via `init_evaluator`)
# ---------------------------------------------------------------------------

_chroma_client = None
_embed_fn = None


def init_evaluator():
    """Initialize ChromaDB client and embedding function. Call once at startup."""
    global _chroma_client, _embed_fn

    if not _HAS_SENTENCE_TRANSFORMERS:
        logger.warning("Skipping evaluator init — sentence-transformers not available")
        return

    settings = get_settings()

    try:
        _chroma_client = chromadb.HttpClient(
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
        logger.info(f"Connected to ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
    except Exception:
        logger.warning("ChromaDB HTTP connection failed — using ephemeral in-process client")
        _chroma_client = chromadb.EphemeralClient()

    _embed_fn = _SentenceTransformerEmbeddingFunction(
        model_name=settings.embedding_model,
    )
    logger.info(f"Loaded embedding model: {settings.embedding_model}")


def get_chroma_client():
    if _chroma_client is None:
        init_evaluator()
    return _chroma_client


def get_embed_fn():
    if _embed_fn is None:
        init_evaluator()
    return _embed_fn


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------

def _keyword_score(query: str, content: str) -> float:
    """Simple keyword-overlap fallback when embeddings are unavailable."""
    query_words = set(query.lower().split())
    content_words = set(content.lower().split())
    if not query_words:
        return 0.5
    overlap = query_words & content_words
    return min(1.0, len(overlap) / max(len(query_words), 1) * 1.2)


def evaluate_relevance(query: str, content: str) -> float:
    """
    Compute cosine similarity between the query and content embeddings.

    Returns a float in [0, 1]. Higher = more relevant.
    Falls back to keyword scoring if embeddings are not available.
    """
    if not _HAS_SENTENCE_TRANSFORMERS:
        return _keyword_score(query, content)

    embed = get_embed_fn()
    if embed is None:
        return _keyword_score(query, content)

    try:
        query_emb = embed([query])[0]
        content_emb = embed([content[:8000]])[0]  # Cap content length for embedding

        # Cosine similarity
        import numpy as np

        q = np.array(query_emb)
        c = np.array(content_emb)
        dot = np.dot(q, c)
        norm = np.linalg.norm(q) * np.linalg.norm(c)
        if norm == 0:
            return 0.0
        similarity = float(dot / norm)
        return max(0.0, min(1.0, similarity))
    except Exception as e:
        logger.error(f"Relevance evaluation failed: {e}")
        return _keyword_score(query, content)


# ---------------------------------------------------------------------------
# Collection management (store & retrieve chunks)
# ---------------------------------------------------------------------------

def store_chunks(
    collection_name: str,
    chunks: list[Chunk],
) -> None:
    """Store text chunks in a ChromaDB collection for later retrieval."""
    if not _HAS_SENTENCE_TRANSFORMERS:
        logger.info("Skipping ChromaDB storage — sentence-transformers not available")
        return

    client = get_chroma_client()
    embed = get_embed_fn()
    if client is None or embed is None:
        return

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=embed,
    )

    if not chunks:
        return

    # Batch upsert
    collection.upsert(
        ids=[c.id for c in chunks],
        documents=[c.content for c in chunks],
        metadatas=[{"source_url": c.source_url, "source_type": c.source_type.value} for c in chunks],
    )
    logger.info(f"Stored {len(chunks)} chunks in collection '{collection_name}'")


def query_chunks(
    collection_name: str,
    query: str,
    n_results: int = 10,
) -> list[str]:
    """Retrieve the top-k most relevant chunks from a collection."""
    if not _HAS_SENTENCE_TRANSFORMERS:
        return []

    client = get_chroma_client()
    embed = get_embed_fn()
    if client is None or embed is None:
        return []

    try:
        collection = client.get_collection(
            name=collection_name,
            embedding_function=embed,
        )
    except Exception:
        logger.warning(f"Collection '{collection_name}' not found")
        return []

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    documents = results.get("documents", [[]])[0]
    return documents


def delete_collection(collection_name: str) -> None:
    """Delete a ChromaDB collection (cleanup after report generation)."""
    if not _HAS_SENTENCE_TRANSFORMERS:
        return

    client = get_chroma_client()
    if client is None:
        return
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass
