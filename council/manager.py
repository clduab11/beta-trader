"""Council knowledge manager — export, keyword search, and semantic search.

Stores ``CouncilRecord`` hashes in Redis db1 under ``council:{uuid}`` keys.
Creates an FTS index on ``merged_text`` and an HNSW vector index on
``embedding_vector`` for hybrid retrieval.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Any
from uuid import UUID

import numpy as np
import structlog
from redis.asyncio import Redis
from redis.commands.search.field import (
    TagField,
    TextField,
    VectorField,
)
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

from council.embedder import EMBEDDING_DIM, JinaEmbedder
from council.types import CouncilRecord

if TYPE_CHECKING:
    from intel.types import IntelResult

log = structlog.get_logger(__name__)

_DEFAULT_REDIS_URL = "redis://localhost:6379/1"
INDEX_NAME = "idx:council"
PREFIX = "council:"


def _float_vector_to_bytes(vec: list[float]) -> bytes:
    """Serialize a float list to a compact binary blob for Redis HNSW."""
    return np.array(vec, dtype=np.float32).tobytes()


class CouncilManager:
    """Async manager for Council knowledge export and retrieval.

    Uses Redis db1 with hash-based storage so both FTS and vector
    indexes can reference the same documents.

    Usage::

        mgr = CouncilManager()
        await mgr.connect()
        record = await mgr.export_result(intel_result)
        hits   = await mgr.search_keyword("some query")
        hits   = await mgr.search_semantic("some query")
        await mgr.close()
    """

    def __init__(
        self,
        redis_url: str | None = None,
        embedder: JinaEmbedder | None = None,
    ) -> None:
        self._redis_url = redis_url or os.environ.get(
            "COUNCIL_REDIS_URL",
            os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL),
        )
        # Force db1 for council isolation
        base = self._redis_url.rsplit("/", 1)[0] if "/" in self._redis_url[8:] else self._redis_url
        self._redis_url = f"{base}/1"

        self._client: Redis | None = None
        self._embedder = embedder or JinaEmbedder()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open Redis connection and ensure indexes exist."""
        if self._client is None:
            self._client = Redis.from_url(self._redis_url, decode_responses=False)
            log.info("CouncilManager connected", url=self._redis_url)
            await self._ensure_indexes()

    async def close(self) -> None:
        """Shut down Redis and embedder connections."""
        if self._client:
            await self._client.aclose()
            self._client = None
        await self._embedder.close()
        log.info("CouncilManager disconnected")

    @property
    def client(self) -> Redis:
        if self._client is None:
            raise RuntimeError("CouncilManager not connected. Call connect() first.")
        return self._client

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    async def _ensure_indexes(self) -> None:
        """Create the combined FTS + HNSW index on council:* hashes."""
        schema = (
            TextField("merged_text", weight=1.0),
            TagField("source_names"),
            TagField("tags"),
            TagField("depth_used"),
            VectorField(
                "embedding_vector",
                algorithm="HNSW",
                attributes={
                    "TYPE": "FLOAT32",
                    "DIM": EMBEDDING_DIM,
                    "DISTANCE_METRIC": "COSINE",
                    "M": 16,
                    "EF_CONSTRUCTION": 200,
                },
            ),
        )

        definition = IndexDefinition(
            prefix=[PREFIX],
            index_type=IndexType.HASH,
        )

        try:
            await self.client.ft(INDEX_NAME).create_index(
                schema, definition=definition
            )
            log.info("Created Council index", name=INDEX_NAME)
        except ResponseError as exc:
            if "Index already exists" in str(exc):
                log.debug("Council index already exists")
            else:
                log.error("Failed to create Council index", error=str(exc))
                raise

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    async def export_result(
        self,
        result: IntelResult,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> CouncilRecord:
        """Export an ``IntelResult`` into the Council knowledge store.

        1. Builds ``merged_text`` from the result.
        2. Calls Jina to embed the merged text.
        3. Persists a Redis hash at ``council:{uuid}``.

        Returns the fully-populated ``CouncilRecord``.
        """
        if not self._client:
            await self.connect()

        merged_text = result.merged_text
        if not merged_text or not merged_text.strip():
            # Fallback: concatenate source snippets
            merged_text = "\n".join(
                s.snippet for s in result.sources if s.snippet
            )

        # Embed
        embedding = await self._embedder.embed(merged_text)

        source_names = list({s.source_name for s in result.sources})

        record = CouncilRecord(
            query_id=result.query_id,
            correlation_id=result.correlation_id,
            merged_text=merged_text,
            embedding_vector=embedding,
            source_names=source_names,
            depth_used=result.depth_used.value
            if hasattr(result.depth_used, "value")
            else str(result.depth_used),
            total_cost_usd=result.total_cost_usd,
            tags=tags or [],
            metadata=metadata or {},
        )

        await self._store_record(record)
        log.info(
            "Exported IntelResult to Council store",
            record_id=str(record.id),
            query_id=record.query_id,
        )
        return record

    async def _store_record(self, record: CouncilRecord) -> None:
        """Persist a CouncilRecord as a Redis hash."""
        key = f"{PREFIX}{record.id}"
        mapping: dict[str, Any] = {
            "query_id": record.query_id,
            "correlation_id": record.correlation_id,
            "merged_text": record.merged_text,
            "embedding_vector": _float_vector_to_bytes(record.embedding_vector),
            "source_names": ",".join(record.source_names),
            "depth_used": record.depth_used,
            "total_cost_usd": str(record.total_cost_usd),
            "tags": ",".join(record.tags),
            "metadata": json.dumps(record.metadata),
            "created_at": record.created_at.isoformat(),
        }
        await self.client.hset(key, mapping=mapping)  # type: ignore[arg-type]

    # ------------------------------------------------------------------
    # Keyword (FTS) search
    # ------------------------------------------------------------------

    async def search_keyword(
        self,
        query_text: str,
        limit: int = 10,
        tags: list[str] | None = None,
    ) -> list[CouncilRecord]:
        """Full-text search over ``merged_text``.

        Args:
            query_text: Free-text query (RediSearch syntax).
            limit: Maximum number of results.
            tags: Optional tag filter (AND logic).

        Returns:
            Matching ``CouncilRecord`` objects sorted by relevance.
        """
        if not self._client:
            await self.connect()

        q_str = query_text
        if tags:
            for tag in tags:
                q_str += f" @tags:{{{tag}}}"

        query = Query(q_str).paging(0, limit).return_fields(
            "query_id",
            "correlation_id",
            "merged_text",
            "source_names",
            "depth_used",
            "total_cost_usd",
            "tags",
            "metadata",
            "created_at",
        )

        try:
            result = await self.client.ft(INDEX_NAME).search(query)
        except ResponseError as exc:
            log.error("Keyword search failed", query=q_str, error=str(exc))
            return []

        return [self._doc_to_record(doc) for doc in result.docs]

    # ------------------------------------------------------------------
    # Semantic (vector) search
    # ------------------------------------------------------------------

    async def search_semantic(
        self,
        query_text: str,
        limit: int = 10,
    ) -> list[CouncilRecord]:
        """Semantic search using Jina embedding + HNSW cosine similarity.

        1. Embeds ``query_text`` via Jina.
        2. Runs a Redis KNN query on ``embedding_vector``.

        Returns:
            Matching ``CouncilRecord`` objects sorted by vector similarity.
        """
        if not self._client:
            await self.connect()

        # Embed the query
        query_vec = await self._embedder.embed(query_text)
        blob = _float_vector_to_bytes(query_vec)

        q = (
            Query(f"*=>[KNN {limit} @embedding_vector $vec AS score]")
            .sort_by("score")
            .paging(0, limit)
            .return_fields(
                "query_id",
                "correlation_id",
                "merged_text",
                "source_names",
                "depth_used",
                "total_cost_usd",
                "tags",
                "metadata",
                "created_at",
                "score",
            )
            .dialect(2)
        )

        try:
            result = await self.client.ft(INDEX_NAME).search(
                q, query_params={"vec": blob}
            )
        except ResponseError as exc:
            log.error("Semantic search failed", error=str(exc))
            return []

        return [self._doc_to_record(doc) for doc in result.docs]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _doc_to_record(doc: Any) -> CouncilRecord:
        """Convert a RediSearch document to a ``CouncilRecord``.

        The ``id`` is extracted from the Redis key (``council:{uuid}``).
        Embedding vector is not returned from search results to save
        bandwidth; it is set to an empty list.
        """
        # doc.id is the full Redis key, e.g. "council:abc-def-..."
        raw_id = doc.id if isinstance(doc.id, str) else doc.id.decode()
        uuid_str = raw_id.replace(PREFIX, "", 1)

        def _get(attr: str, default: str = "") -> str:
            val = getattr(doc, attr, default)
            if isinstance(val, bytes):
                return val.decode()
            return val or default

        source_names_raw = _get("source_names")
        tags_raw = _get("tags")
        metadata_raw = _get("metadata", "{}")

        return CouncilRecord(
            id=UUID(uuid_str),
            query_id=_get("query_id"),
            correlation_id=_get("correlation_id"),
            merged_text=_get("merged_text"),
            embedding_vector=[],  # not returned from search
            source_names=[s for s in source_names_raw.split(",") if s],
            depth_used=_get("depth_used", "STANDARD"),
            total_cost_usd=float(_get("total_cost_usd", "0.0")),
            tags=[t for t in tags_raw.split(",") if t],
            metadata=json.loads(metadata_raw) if metadata_raw else {},
        )
