"""Shared type definitions for the Intel layer.

Implements types from docs/interfaces/types.md:
- IntelQuery, IntelDepth, IntelResult, IntelSource
- Timestamp helper
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class IntelDepth(StrEnum):
    """Controls how many sources the Intel Orchestrator queries and at what cost."""

    SHALLOW = "SHALLOW"
    STANDARD = "STANDARD"
    DEEP = "DEEP"


class Timestamp(BaseModel):
    """Canonical timestamp format used across all layers."""

    unix_nanos: int = Field(description="Nanosecond-precision Unix timestamp")
    iso8601: str = Field(description="ISO 8601 formatted timestamp string")

    @classmethod
    def now(cls) -> Timestamp:
        """Create a Timestamp for the current moment."""
        now = datetime.now(UTC)
        unix_nanos = int(now.timestamp() * 1_000_000_000)
        return cls(unix_nanos=unix_nanos, iso8601=now.isoformat())

    @classmethod
    def from_epoch_seconds(cls, epoch: float) -> Timestamp:
        """Create a Timestamp from epoch seconds."""
        dt = datetime.fromtimestamp(epoch, tz=UTC)
        return cls(unix_nanos=int(epoch * 1_000_000_000), iso8601=dt.isoformat())


class IntelSource(BaseModel):
    """Individual source result within an IntelResult."""

    source_name: str = Field(description='e.g. "exa", "tavily", "firecrawl"')
    url: str | None = Field(default=None, description="Source URL if applicable")
    title: str = Field(description="Title or heading of the result")
    snippet: str = Field(description="Relevant text excerpt")
    relevance_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="0.0–1.0 relevance ranking"
    )
    cost_usd: float = Field(default=0.0, ge=0.0, description="Cost of this individual call")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Source-specific latency")


class IntelResult(BaseModel):
    """Aggregated intelligence output from one or more sources."""

    query_id: str = Field(description="Matches the originating IntelQuery.query_id")
    correlation_id: str = Field(description="For cross-layer tracing")
    sources: list[IntelSource] = Field(default_factory=list)
    merged_text: str = Field(default="", description="Deduplicated, ranked text summary")
    embeddings: list[list[float]] | None = Field(
        default=None, description="Jina embeddings when depth is DEEP"
    )
    depth_used: IntelDepth = Field(description="Actual depth that was executed")
    total_cost_usd: float = Field(default=0.0, ge=0.0, description="Aggregated cost")
    latency_ms: float = Field(default=0.0, ge=0.0, description="Wall-clock time")
    timestamp: Timestamp = Field(default_factory=Timestamp.now)
    cached: bool = Field(default=False, description="Whether result was served from Redis cache")


class IntelQuery(BaseModel):
    """Standardized query structure submitted to the Intel Orchestrator."""

    query_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str = Field(description="Natural language query string")
    depth: IntelDepth = Field(default=IntelDepth.STANDARD)
    max_sources: int = Field(default=10, ge=1, description="Upper bound on sources to consult")
    cache_ttl_seconds: int | None = Field(
        default=None, description="Override default cache TTL; None uses per-source defaults"
    )
    correlation_id: str = Field(default_factory=lambda: f"req-{uuid.uuid4().hex[:12]}")
    timestamp: Timestamp = Field(default_factory=Timestamp.now)


class SearchResult(BaseModel):
    """Raw search result from an individual source before merging."""

    url: str | None = None
    title: str = ""
    snippet: str = ""
    relevance_score: float = 0.0
    source_name: str = ""
    raw_data: dict | None = None


class ScrapedContent(BaseModel):
    """Content scraped from a single URL via Firecrawl."""

    url: str
    title: str = ""
    content: str = ""
    markdown: str = ""
    metadata: dict = Field(default_factory=dict)
    cost_usd: float = 0.0
    latency_ms: float = 0.0
