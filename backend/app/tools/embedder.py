"""Embedding service — local sentence-transformers with Cohere & OpenAI fallbacks.

Priority:
1. sentence-transformers (all-MiniLM-L6-v2) — free, offline, 384-dim
2. Cohere embed-english-light-v3.0 — if COHERE_API_KEY is set and ST fails
3. OpenAI text-embedding-3-small — if OPENAI_API_KEY is set and above fail
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_ST_MODEL = None  # lazy-loaded sentence-transformers model
_ST_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_st_model():
    """Lazily load the sentence-transformers model."""
    global _ST_MODEL
    if _ST_MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading sentence-transformers model: {_ST_MODEL_NAME}")
            _ST_MODEL = SentenceTransformer(_ST_MODEL_NAME)
            logger.info("sentence-transformers model loaded ✓")
        except ImportError:
            logger.warning("sentence-transformers not installed — pip install sentence-transformers")
            _ST_MODEL = None
        except Exception as e:
            logger.warning(f"Failed to load sentence-transformers: {e}")
            _ST_MODEL = None
    return _ST_MODEL


def embed_texts(texts: list[str]) -> Optional[list[list[float]]]:
    """
    Embed a list of texts into dense vectors.

    Returns list of float lists (one per text), or None if embedding is unavailable.
    Tries sentence-transformers first, then OpenAI as fallback.
    """
    if not texts:
        return []

    # --- Strategy 1: sentence-transformers (local, free) ---
    model = _get_st_model()
    if model is not None:
        try:
            embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
            return embeddings.tolist()
        except Exception as e:
            logger.warning(f"sentence-transformers embedding failed: {e}")

    # --- Strategy 2: Cohere embed-english-light-v3.0 ---
    cohere_key = os.environ.get("COHERE_API_KEY", "")
    if cohere_key:
        try:
            import cohere
            co = cohere.ClientV2(api_key=cohere_key)
            response = co.embed(
                texts=texts,
                model="embed-english-light-v3.0",
                input_type="search_document",
                embedding_types=["float"],
            )
            return [list(e) for e in response.embeddings.float_]
        except Exception as e:
            logger.warning(f"Cohere embedding failed: {e}")

    # --- Strategy 3: OpenAI text-embedding-3-small ---
    openai_key = os.environ.get("OPENAI_API_KEY", "")
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts,
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.warning(f"OpenAI embedding failed: {e}")

    logger.warning("No embedding backend available — hybrid search will use BM25 only")
    return None


def embed_single(text: str) -> Optional[list[float]]:
    """Embed a single text. Returns None if no embedding backend is available."""
    results = embed_texts([text])
    if results is None or len(results) == 0:
        return None
    return results[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(va, vb) / (norm_a * norm_b))


def embedding_to_json(embedding: Optional[list[float]]) -> Optional[str]:
    """Serialize an embedding to a JSON string for storage."""
    if embedding is None:
        return None
    return json.dumps(embedding)


def embedding_from_json(json_str: Optional[str]) -> Optional[list[float]]:
    """Deserialize an embedding from a JSON string."""
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except Exception:
        return None


# ── Pinecone Integration ──────────────────────────────────────────────────

async def store_embeddings_in_pinecone(chunks: list[dict]) -> bool:
    """
    Store chunk embeddings in Pinecone for semantic search.
    
    chunks format: [
        {"id": "chunk_123", "text": "Chapter 1...", "metadata": {"source_id": "pdf_1", ...}},
        ...
    ]
    """
    if not chunks:
        return True
    
    from app.tools.pinecone_client import upsert_embeddings
    
    # Embed all texts
    texts = [c.get("text", "") for c in chunks]
    embeddings = embed_texts(texts)
    
    if not embeddings:
        logger.warning("Could not generate embeddings for Pinecone storage")
        return False
    
    # Prepare Pinecone vectors
    vectors = [
        {
            "id": chunk["id"],
            "values": embedding,
            "metadata": chunk.get("metadata", {})
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    
    return await upsert_embeddings(vectors)


async def search_similar(query: str, top_k: int = 10) -> list[dict]:
    """
    Search for semantically similar documents in Pinecone.
    
    Returns: [
        {"chunk_id": "chunk_123", "score": 0.95, "metadata": {...}},
        ...
    ]
    """
    from app.tools.pinecone_client import search_embeddings
    
    # Embed query
    query_embedding = embed_single(query)
    if not query_embedding:
        logger.warning("Could not embed query for semantic search")
        return []
    
    # Search Pinecone
    results = await search_embeddings(query_embedding, top_k=top_k)
    return results
