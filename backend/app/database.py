"""SQLAlchemy models and database setup for the Deep Research Platform."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from sqlalchemy.pool import NullPool


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
    """A text chunk from a source, used for hybrid BM25 + vector retrieval."""
    __tablename__ = "chunks"

    id = Column(String, primary_key=True)
    source_id = Column(String, ForeignKey("sources.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    chunk_index = Column(Integer, default=0)
    section_heading = Column(String, default="")
    char_count = Column(Integer, default=0)
    embedding = Column(Text, default=None)  # JSON-encoded float list (sentence-transformers)

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


class User(Base):
    """A registered user (anonymous or authenticated)."""
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=True, index=True)  # Optional for anonymous users
    name = Column(String, default="")
    is_anonymous = Column(Integer, default=1)  # 1 = anonymous, 0 = authenticated
    preferences_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

    @property
    def preferences(self) -> dict:
        try:
            return json.loads(self.preferences_json)
        except Exception:
            return {}

    @preferences.setter
    def preferences(self, value: dict):
        self.preferences_json = json.dumps(value, default=str)


class Conversation(Base):
    """A conversation thread containing multiple messages."""
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="New Research")
    summary = Column(Text, default="")  # Auto-generated summary of the conversation
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    """A single message in a conversation (user question or AI response)."""
    __tablename__ = "messages"

    id = Column(String, primary_key=True)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    role = Column(String, nullable=False)  # "user" | "assistant" | "system"
    content = Column(Text, nullable=False)
    extra_data_json = Column(Text, default="{}")  # tokens_used, cost_usd, report_id, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    conversation = relationship("Conversation", back_populates="messages")

    @property
    def extra_data(self) -> dict:
        try:
            return json.loads(self.extra_data_json)
        except Exception:
            return {}

    @extra_data.setter
    def extra_data(self, value: dict):
        self.extra_data_json = json.dumps(value, default=str)


class UserPreference(Base):
    """Individual user preference key-value pairs."""
    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    key = Column(String, nullable=False, index=True)  # "code_examples", "verbose", "source_format"
    value = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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

    engine_kwargs = {"echo": False}
    if database_url.startswith("sqlite+"):
        engine_kwargs["poolclass"] = NullPool

    _engine = create_async_engine(database_url, **engine_kwargs)
    _session_factory = sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_session_factory():
    """Return the async session factory."""
    if _session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _session_factory
