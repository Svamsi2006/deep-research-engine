"""Shared Pydantic models / DTOs used across the pipeline."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class UrlCategory(str, Enum):
    DOC = "doc"
    GITHUB = "github"
    PDF = "pdf"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Data Transfer Objects
# ---------------------------------------------------------------------------

class SearchResult(BaseModel):
    """A single search result from DuckDuckGo or Tavily."""
    title: str = ""
    url: str
    snippet: str = ""
    source: str = "duckduckgo"  # "duckduckgo" | "tavily"
    relevance_score: float = 0.0


class ScrapedDocument(BaseModel):
    """Content extracted from a web page."""
    url: str
    title: str = ""
    content: str = ""
    content_type: UrlCategory = UrlCategory.DOC
    char_count: int = 0
    scraped_at: datetime = Field(default_factory=datetime.utcnow)

    def model_post_init(self, __context):
        if self.char_count == 0 and self.content:
            self.char_count = len(self.content)


class RepoInfo(BaseModel):
    """Metadata + key files from a cloned GitHub repo."""
    url: str
    name: str = ""
    readme: str = ""
    file_tree: list[str] = Field(default_factory=list)
    key_files: dict[str, str] = Field(default_factory=dict)  # path -> content
    stars: int = 0
    cloned_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    """A processed, embeddable text chunk."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    source_url: str = ""
    source_type: UrlCategory = UrlCategory.DOC
    metadata: dict = Field(default_factory=dict)
