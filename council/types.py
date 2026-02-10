"""Type definitions for the Council module."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class KnowledgeSource(StrEnum):
    """Source of the knowledge item."""

    INTEL = "intel"
    USER = "user"
    SYSTEM = "system"
    STRATEGY = "strategy"
    COUNCIL = "council"


class KnowledgeItem(BaseModel):
    """A unit of knowledge stored by the Council.

    Attributes:
        id: Unique identifier for the item.
        content: The actual knowledge content (text, JSON string, etc).
        source: Origin of the information.
        tags: Taxonomy tags for retrieval.
        metadata: Additional structured data.
        created_at: Timestamp of creation.
        expires_at: Optional expiration timestamp.
    """

    id: UUID = Field(default_factory=uuid4)
    content: str
    source: KnowledgeSource
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None


class CouncilRecord(BaseModel):
    """Record exported from the Council into the knowledge store.

    Combines an IntelResult's merged_text with its embedding vector and
    source metadata so it can be indexed for FTS and HNSW vector search.

    Attributes:
        id: Unique record identifier.
        query_id: The originating IntelQuery.query_id.
        correlation_id: Cross-layer tracing id.
        merged_text: Deduplicated, ranked text from the IntelResult.
        embedding_vector: Float vector produced by Jina embedder.
        source_names: Names of contributing intel sources.
        depth_used: Intel depth that was executed.
        total_cost_usd: Aggregated cost of producing this intel.
        tags: Taxonomy tags for filtering.
        metadata: Additional structured data.
        created_at: Timestamp of creation.
    """

    id: UUID = Field(default_factory=uuid4)
    query_id: str
    correlation_id: str = ""
    merged_text: str
    embedding_vector: list[float] = Field(default_factory=list)
    source_names: list[str] = Field(default_factory=list)
    depth_used: str = "STANDARD"
    total_cost_usd: float = Field(default=0.0, ge=0.0)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("merged_text")
    @classmethod
    def merged_text_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("merged_text must not be empty")
        return v

    @field_validator("embedding_vector")
    @classmethod
    def embedding_dimensions_check(cls, v: list[float]) -> list[float]:
        # Allow empty (pre-embedding) but if present must be 768-dim (Jina v2 default)
        if v and len(v) != 768:
            raise ValueError(
                f"embedding_vector must have 768 dimensions, got {len(v)}"
            )
        return v
