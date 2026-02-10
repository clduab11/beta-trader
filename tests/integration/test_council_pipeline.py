"""Integration tests for Council knowledge pipeline (mock Jina + mock Redis).

Exercises the full export → search_keyword → search_semantic flow
with mocked external services.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import numpy as np
import pytest
from redis.exceptions import ResponseError

from council.embedder import EMBEDDING_DIM, JinaEmbedder
from council.manager import CouncilManager, PREFIX, INDEX_NAME, _float_vector_to_bytes
from council.types import CouncilRecord
from intel.types import IntelDepth, IntelResult, IntelSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VEC = [0.02] * EMBEDDING_DIM


def _intel_result(merged: str = "integration test intel", **kw) -> IntelResult:
    defaults = dict(
        query_id=f"q-{uuid4().hex[:8]}",
        correlation_id=f"corr-{uuid4().hex[:8]}",
        sources=[
            IntelSource(source_name="exa", title="T1", snippet="s1", relevance_score=0.8),
            IntelSource(source_name="tavily", title="T2", snippet="s2", relevance_score=0.7),
        ],
        merged_text=merged,
        depth_used=IntelDepth.DEEP,
        total_cost_usd=0.01,
    )
    defaults.update(kw)
    return IntelResult(**defaults)


def _doc_from_record(record: CouncilRecord) -> MagicMock:
    """Simulate the RediSearch doc returned after indexing a record."""
    doc = MagicMock()
    doc.id = f"{PREFIX}{record.id}"
    doc.query_id = record.query_id
    doc.correlation_id = record.correlation_id
    doc.merged_text = record.merged_text
    doc.source_names = ",".join(record.source_names)
    doc.depth_used = record.depth_used
    doc.total_cost_usd = str(record.total_cost_usd)
    doc.tags = ",".join(record.tags)
    doc.metadata = json.dumps(record.metadata)
    doc.created_at = record.created_at.isoformat()
    return doc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    client = AsyncMock()
    ft_mock = AsyncMock()
    ft_mock.create_index = AsyncMock()
    ft_mock.search = AsyncMock()
    client.ft = MagicMock(return_value=ft_mock)
    client.hset = AsyncMock()
    return client


@pytest.fixture
def mock_embedder():
    emb = AsyncMock(spec=JinaEmbedder)
    emb.embed = AsyncMock(return_value=list(_VEC))
    emb.close = AsyncMock()
    emb.is_rate_limited = False
    return emb


@pytest.fixture
def manager(mock_redis, mock_embedder):
    mgr = CouncilManager(embedder=mock_embedder)
    mgr._client = mock_redis
    return mgr


# ---------------------------------------------------------------------------
# Integration: Export → Keyword search
# ---------------------------------------------------------------------------

class TestExportThenKeywordSearch:

    @pytest.mark.asyncio
    async def test_export_then_search_keyword(self, manager, mock_redis, mock_embedder):
        """Full round-trip: export an IntelResult then find it via keyword search."""
        result = _intel_result(merged="polymarket BTC prediction")
        record = await manager.export_result(result, tags=["btc", "prediction"])

        # Verify export called embed + hset
        mock_embedder.embed.assert_called_once_with("polymarket BTC prediction")
        mock_redis.hset.assert_called_once()

        # Simulate that keyword search returns the record we just stored
        doc = _doc_from_record(record)
        search_result = MagicMock()
        search_result.docs = [doc]
        mock_redis.ft.return_value.search.return_value = search_result

        hits = await manager.search_keyword("BTC prediction")
        assert len(hits) == 1
        assert hits[0].id == record.id
        assert hits[0].merged_text == "polymarket BTC prediction"
        assert "btc" in hits[0].tags


# ---------------------------------------------------------------------------
# Integration: Export → Semantic search
# ---------------------------------------------------------------------------

class TestExportThenSemanticSearch:

    @pytest.mark.asyncio
    async def test_export_then_search_semantic(self, manager, mock_redis, mock_embedder):
        """Full round-trip: export then find via vector similarity."""
        result = _intel_result(merged="kalshi event probability shift")
        record = await manager.export_result(result, tags=["kalshi"])

        doc = _doc_from_record(record)
        doc.score = "0.95"
        search_result = MagicMock()
        search_result.docs = [doc]
        mock_redis.ft.return_value.search.return_value = search_result

        # Semantic search should call embed again for the query
        mock_embedder.embed.reset_mock()
        hits = await manager.search_semantic("event probability")
        mock_embedder.embed.assert_called_once_with("event probability")

        assert len(hits) == 1
        assert hits[0].id == record.id

        # Verify vector blob was passed as query param
        search_call = mock_redis.ft.return_value.search.call_args
        vec_blob = search_call[1]["query_params"]["vec"]
        assert isinstance(vec_blob, bytes)
        assert len(vec_blob) == EMBEDDING_DIM * 4


# ---------------------------------------------------------------------------
# Integration: Error paths
# ---------------------------------------------------------------------------

class TestCouncilErrorPaths:

    @pytest.mark.asyncio
    async def test_export_embedder_failure_propagates(self, manager, mock_embedder):
        """If Jina fails, the error should bubble up from export_result."""
        from intel.errors import APIError

        mock_embedder.embed.side_effect = APIError(
            message="Jina down",
            source_module="council.embedder",
            service_name="jina",
            http_status=503,
        )

        result = _intel_result()
        with pytest.raises(APIError, match="Jina down"):
            await manager.export_result(result)

    @pytest.mark.asyncio
    async def test_keyword_search_redis_error(self, manager, mock_redis):
        """Redis error during keyword search returns empty list."""
        mock_redis.ft.return_value.search.side_effect = ResponseError("index gone")
        hits = await manager.search_keyword("anything")
        assert hits == []

    @pytest.mark.asyncio
    async def test_semantic_search_redis_error(self, manager, mock_redis, mock_embedder):
        """Redis error during vector search returns empty list."""
        mock_redis.ft.return_value.search.side_effect = ResponseError("HNSW error")
        hits = await manager.search_semantic("anything")
        assert hits == []

    @pytest.mark.asyncio
    async def test_index_creation_non_duplicate_error_raises(self, manager, mock_redis):
        """Non-'already exists' ResponseError should propagate."""
        mock_redis.ft.return_value.create_index.side_effect = ResponseError(
            "Unknown command"
        )
        with pytest.raises(ResponseError, match="Unknown command"):
            await manager._ensure_indexes()


# ---------------------------------------------------------------------------
# Integration: Multiple exports
# ---------------------------------------------------------------------------

class TestMultipleExports:

    @pytest.mark.asyncio
    async def test_multiple_exports_unique_keys(self, manager, mock_redis, mock_embedder):
        """Each export should create a unique Redis key."""
        r1 = _intel_result(merged="first result")
        r2 = _intel_result(merged="second result")

        rec1 = await manager.export_result(r1)
        rec2 = await manager.export_result(r2)

        assert rec1.id != rec2.id
        assert mock_redis.hset.call_count == 2

        keys = [call[0][0] for call in mock_redis.hset.call_args_list]
        assert keys[0] != keys[1]
        assert all(k.startswith(PREFIX) for k in keys)
