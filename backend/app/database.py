"""SQLAlchemy models and database setup for report persistence."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


class ReportRow(Base):
    __tablename__ = "reports"

    id = Column(String, primary_key=True)
    query = Column(String, nullable=False, index=True)
    report = Column(Text, default="")
    evaluation_score = Column(Float, default=0.0)
    retry_count = Column(Integer, default=0)
    thought_trace_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def thought_trace(self) -> list[dict]:
        try:
            return json.loads(self.thought_trace_json)
        except Exception:
            return []

    @thought_trace.setter
    def thought_trace(self, value: list[dict]):
        self.thought_trace_json = json.dumps(value, default=str)


# ---------------------------------------------------------------------------
# Engine & session factory (async)
# ---------------------------------------------------------------------------

_engine = None
_session_factory = None


async def init_db(database_url: str):
    """Create database tables and initialize the async engine."""
    global _engine, _session_factory

    _engine = create_async_engine(database_url, echo=False)
    _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory():
    """Return the async session factory."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory
