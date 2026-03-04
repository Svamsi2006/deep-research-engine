"""Pinecone vector database client — manages embeddings and semantic search."""

from __future__ import annotations

import logging
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)

_PINECONE_INDEX = None  # Lazy-loaded Pinecone index


def get_pinecone_index():
    """Lazily initialize and return Pinecone index."""
    global _PINECONE_INDEX
    if _PINECONE_INDEX is None:
        try:
            from pinecone import Pinecone
            
            settings = get_settings()
            if not settings.pinecone_api_key:
                logger.warning("Pinecone API key not set — vector search disabled")
                return None
            
            pc = Pinecone(api_key=settings.pinecone_api_key)
            _PINECONE_INDEX = pc.Index(settings.pinecone_index_name)
            logger.info(f"✓ Connected to Pinecone index: {settings.pinecone_index_name}")
        except ImportError:
            logger.error("pinecone-client not installed — pip install pinecone-client")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            return None
    
    return _PINECONE_INDEX


async def upsert_embeddings(
    vectors: list[dict],
    namespace: str = "documents"
) -> bool:
    """
    Upsert embeddings to Pinecone.
    
    vectors format: [
        {"id": "chunk_123", "values": [0.1, 0.2, ...], "metadata": {"source": "pdf", ...}},
        ...
    ]
    """
    try:
        index = get_pinecone_index()
        if not index:
            logger.warning("Pinecone not available — using only BM25 search")
            return False
        
        index.upsert(vectors=vectors, namespace=namespace)
        logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
        return True
    except Exception as e:
        logger.error(f"Failed to upsert to Pinecone: {e}")
        return False


async def search_embeddings(
    query_vector: list[float],
    top_k: int = 10,
    namespace: str = "documents"
) -> list[dict]:
    """
    Search for similar vectors in Pinecone.
    
    Returns: [
        {"id": "chunk_123", "score": 0.95, "metadata": {...}},
        ...
    ]
    """
    try:
        index = get_pinecone_index()
        if not index:
            return []
        
        results = index.query(
            vector=query_vector,
            top_k=top_k,
            namespace=namespace,
            include_metadata=True
        )
        
        hits = []
        for match in results.get("matches", []):
            hits.append({
                "id": match["id"],
                "score": match["score"],
                "metadata": match.get("metadata", {})
            })
        
        return hits
    except Exception as e:
        logger.error(f"Failed to search Pinecone: {e}")
        return []


async def delete_namespace(namespace: str = "documents") -> bool:
    """Delete all vectors in a namespace."""
    try:
        index = get_pinecone_index()
        if not index:
            return False
        
        index.delete(delete_all=True, namespace=namespace)
        logger.info(f"Deleted namespace: {namespace}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete namespace: {e}")
        return False
