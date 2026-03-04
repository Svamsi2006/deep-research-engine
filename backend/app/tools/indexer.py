"""Hybrid Indexer — BM25 keyword search + cosine vector search fused with RRF.

Fallback: if no embeddings are stored, behaves exactly like the old BM25-only indexer.
"""

from __future__ import annotations

import logging
import math
import re
import uuid
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class IndexChunk:
    """A chunk ready for indexing (with optional embedding)."""
    id: str
    source_id: str
    content: str
    chunk_index: int
    section_heading: str
    embedding: Optional[list[float]] = field(default=None)


@dataclass
class SearchResult:
    """A search hit with a combined hybrid score."""
    chunk_id: str
    source_id: str
    content: str
    section_heading: str
    score: float


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)


def chunk_text(
    text: str,
    source_id: str,
    chunk_size: int = 600,
    chunk_overlap: int = 100,
) -> list[IndexChunk]:
    """
    Split text into section-aware chunks.

    Strategy:
    1. Split on markdown headings first (preserves section context)
    2. Within each section, split by paragraph/sentence to target chunk_size chars
    3. Each chunk carries its section heading for context
    """
    if not text.strip():
        return []

    # Find all headings and their positions
    sections: list[tuple[str, str]] = []  # (heading, content)
    heading_matches = list(_HEADING_RE.finditer(text))

    if not heading_matches:
        # No headings — treat whole text as one section
        sections = [("", text)]
    else:
        # Content before first heading
        if heading_matches[0].start() > 0:
            sections.append(("", text[: heading_matches[0].start()].strip()))

        for i, match in enumerate(heading_matches):
            heading = match.group(2).strip()
            start = match.end()
            end = heading_matches[i + 1].start() if i + 1 < len(heading_matches) else len(text)
            content = text[start:end].strip()
            if content:
                sections.append((heading, content))

    # Split each section into chunks
    chunks: list[IndexChunk] = []
    idx = 0

    for heading, content in sections:
        if len(content) <= chunk_size:
            chunks.append(IndexChunk(
                id=str(uuid.uuid4()),
                source_id=source_id,
                content=content,
                chunk_index=idx,
                section_heading=heading,
            ))
            idx += 1
        else:
            # Split by paragraphs, then combine to target size
            paragraphs = re.split(r"\n\n+", content)
            current = ""

            for para in paragraphs:
                if len(current) + len(para) + 2 <= chunk_size:
                    current = (current + "\n\n" + para).strip()
                else:
                    if current:
                        chunks.append(IndexChunk(
                            id=str(uuid.uuid4()),
                            source_id=source_id,
                            content=current,
                            chunk_index=idx,
                            section_heading=heading,
                        ))
                        idx += 1
                        # Keep overlap
                        overlap_text = current[-chunk_overlap:] if len(current) > chunk_overlap else ""
                        current = (overlap_text + "\n\n" + para).strip()
                    else:
                        current = para

            if current.strip():
                chunks.append(IndexChunk(
                    id=str(uuid.uuid4()),
                    source_id=source_id,
                    content=current,
                    chunk_index=idx,
                    section_heading=heading,
                ))
                idx += 1

    logger.info(f"Chunked source {source_id}: {len(chunks)} chunks from {len(text)} chars")
    return chunks


# ---------------------------------------------------------------------------
# BM25 Search (pure Python, no deps)
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    """Simple whitespace + punctuation tokenizer."""
    return re.findall(r"\w+", text.lower())


class BM25Index:
    """Lightweight BM25 index over a list of chunks."""

    def __init__(self, chunks: list[IndexChunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b

        # Tokenize all docs
        self.doc_tokens = [_tokenize(c.content) for c in chunks]
        self.doc_lens = [len(t) for t in self.doc_tokens]
        self.avgdl = sum(self.doc_lens) / max(len(self.doc_lens), 1)
        self.n_docs = len(chunks)

        # Build DF (document frequency)
        self.df: Counter = Counter()
        for tokens in self.doc_tokens:
            unique = set(tokens)
            for t in unique:
                self.df[t] += 1

    def search(self, query: str, top_k: int = 10) -> list[SearchResult]:
        """Search chunks by BM25 score."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        scores: list[float] = []

        for i, doc_tokens in enumerate(self.doc_tokens):
            score = 0.0
            tf_counter = Counter(doc_tokens)
            dl = self.doc_lens[i]

            for qt in query_tokens:
                if qt not in self.df:
                    continue
                tf = tf_counter.get(qt, 0)
                df = self.df[qt]
                idf = math.log((self.n_docs - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
                score += idf * tf_norm

            scores.append(score)

        # Rank
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)

        results = []
        for idx, sc in ranked[:top_k]:
            if sc > 0:
                c = self.chunks[idx]
                results.append(SearchResult(
                    chunk_id=c.id,
                    source_id=c.source_id,
                    content=c.content,
                    section_heading=c.section_heading,
                    score=round(sc, 4),
                ))

        return results


def build_index(chunks: list[IndexChunk]) -> BM25Index:
    """Build a BM25 index from chunks."""
    return BM25Index(chunks)


# ---------------------------------------------------------------------------
# Vector Search (cosine similarity from stored embeddings)
# ---------------------------------------------------------------------------

def _cosine(a: list[float], b: list[float]) -> float:
    """Pure-Python cosine similarity (no numpy needed at index time)."""
    try:
        import numpy as np
        va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
        na, nb = np.linalg.norm(va), np.linalg.norm(vb)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(va, vb) / (na * nb))
    except ImportError:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na > 0 and nb > 0 else 0.0


def vector_search(
    query_embedding: list[float],
    chunks: list[IndexChunk],
    top_k: int = 10,
) -> list[SearchResult]:
    """Return top-k chunks by cosine similarity to query_embedding."""
    if not query_embedding or not chunks:
        return []

    scored = []
    for chunk in chunks:
        if chunk.embedding is None:
            continue
        score = _cosine(query_embedding, chunk.embedding)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        SearchResult(
            chunk_id=c.id,
            source_id=c.source_id,
            content=c.content,
            section_heading=c.section_heading,
            score=round(sc, 4),
        )
        for sc, c in scored[:top_k]
        if sc > 0.05  # discard near-zero matches
    ]


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion (RRF) — fuse BM25 + vector results
# ---------------------------------------------------------------------------

def _rrf(rankings: list[list[SearchResult]], k: int = 60) -> list[SearchResult]:
    """
    Reciprocal Rank Fusion of multiple ranked lists.

    RRF score = Σ 1 / (rank + k)  for each result across all lists.
    """
    scores: dict[str, float] = {}
    best: dict[str, SearchResult] = {}

    for ranked_list in rankings:
        for rank, result in enumerate(ranked_list):
            cid = result.chunk_id
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (rank + k)
            if cid not in best:
                best[cid] = result

    merged = []
    for cid, rrf_score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        r = best[cid]
        merged.append(SearchResult(
            chunk_id=r.chunk_id,
            source_id=r.source_id,
            content=r.content,
            section_heading=r.section_heading,
            score=round(rrf_score, 6),
        ))

    return merged


def hybrid_search(
    query: str,
    chunks: list[IndexChunk],
    top_k: int = 15,
) -> list[SearchResult]:
    """
    Hybrid BM25 + vector search fused with Reciprocal Rank Fusion.

    If no embeddings are stored on the chunks, falls back to BM25 only.
    If no LLM API key is configured, proceeds with BM25 only.
    """
    bm25_index = build_index(chunks)
    bm25_results = bm25_index.search(query, top_k=top_k * 2)

    # Check if any chunks have embeddings
    has_embeddings = any(c.embedding is not None for c in chunks)

    if not has_embeddings:
        logger.debug("No embeddings found — using BM25 only")
        return bm25_results[:top_k]

    # Embed the query
    try:
        from app.tools.embedder import embed_single
        query_embedding = embed_single(query)
    except Exception as e:
        logger.warning(f"Query embedding failed: {e} — using BM25 only")
        return bm25_results[:top_k]

    if query_embedding is None:
        return bm25_results[:top_k]

    vector_results = vector_search(query_embedding, chunks, top_k=top_k * 2)

    if not vector_results:
        return bm25_results[:top_k]

    # Fuse with RRF
    fused = _rrf([bm25_results, vector_results])
    logger.info(f"Hybrid search: BM25={len(bm25_results)}, vector={len(vector_results)}, fused={len(fused)}")
    return fused[:top_k]

