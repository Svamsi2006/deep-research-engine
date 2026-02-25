"""SQLAlchemy models and database setup for the Deep Research Platform."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Source(Base):
    """An ingested source document (PDF, URL, or GitHub repo)."""
    __tablename__ = "sources"

    id = Column(String, primary_key=True)
    source_type = Column(String, nullable=False)  # "pdf", "url", "github"
    origin = Column(String, nullable=False)         # URL or filename
    title = Column(String, default="")
    raw_text = Column(Text, default="")
    char_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    chunks = relationship("ChunkRow", back_populates="source", cascade="all, delete-orphan")


class ChunkRow(Base):
    """A text chunk from a source, used for BM25 retrieval."""
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    section_heading = Column(String, default="")
    char_count = Column(Integer, default=0)

    source = relationship("Source", back_populates="chunks")


class ReportRow(Base):
    """A generated research report."""
    __tablename__ = "reports"

    id = Column(String, primary_key=True)
    question = Column(String, nullable=False, index=True)
    report_md = Column(Text, default="")
    sources_json = Column(Text, default="[]")
    flashcards_json = Column(Text, default="[]")
    evaluation_score = Column(Float, default=0.0)
    pipeline_log_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def sources_used(self) -> list[dict]:
        try:
            return json.loads(self.sources_json)
        except Exception:
            return []

    @sources_used.setter
    def sources_used(self, value: list[dict]):
        self.sources_json = json.dumps(value, default=str)

    @property
    def flashcards(self) -> list[dict]:
        try:
            return json.loads(self.flashcards_json)
        except Exception:
            return []

    @flashcards.setter
    def flashcards(self, value: list[dict]):
        self.flashcards_json = json.dumps(value, default=str)

    @property
    def pipeline_log(self) -> list[dict]:
        try:
            return json.loads(self.pipeline_log_json)
        except Exception:
            return []

    @pipeline_log.setter
    def pipeline_log(self, value: list[dict]):
        self.pipeline_log_json = json.dumps(value, default=str)


# ---------------------------------------------------------------------------
# Engine & session factory (async)
# ---------------------------------------------------------------------------

_engine = None
_session_factory = None


async def init_db(database_url: str):
    """Create database tables and initialize the async engine."""
    global _engine, _session_factory

    # Handle Postgres URLs (Render/Supabase give postgres:// but SQLAlchemy async needs postgresql+asyncpg://)
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://") and not database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    _engine = create_async_engine(database_url, echo=False)
    _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory():
    """Return the async session factory."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory
