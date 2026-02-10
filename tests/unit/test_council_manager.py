"""Unit tests for CouncilManager — export, keyword search, semantic search."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import numpy as np
import pytest
from redis.exceptions import ResponseError

from council.embedder import EMBEDDING_DIM
from council.manager import CouncilManager, PREFIX, INDEX_NAME, _float_vector_to_bytes
from council.types import CouncilRecord
from intel.types import IntelDepth, IntelResult, IntelSource


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_vector(dim: int = EMBEDDING_DIM) -> list[float]:
    return [0.01] * dim


def _make_intel_result(**overrides) -> IntelResult:
    defaults = dict(
        query_id="q-test",
        correlation_id="corr-test",
        sources=[
            IntelSource(
                source_name="exa",
                title="Test",
                snippet="snippet text",
                relevance_score=0.9,
            ),
        ],
        merged_text="merged intel text for testing",
        depth_used=IntelDepth.STANDARD,
        total_cost_usd=0.005,
    )
    defaults.update(overrides)
    return IntelResult(**defaults)


def _fake_search_doc(record_id: UUID | None = None, merged_text: str = "found it"):
    """Return a mock RediSearch document object."""
    rid = record_id or uuid4()
    doc = MagicMock()
    doc.id = f"{PREFIX}{rid}"
    doc.query_id = "q-test"
    doc.correlation_id = "corr-test"
    doc.merged_text = merged_text
    doc.source_names = "exa,tavily"
    doc.depth_used = "STANDARD"
    doc.total_cost_usd = "0.005"
    doc.tags = "crypto,news"
    doc.metadata = '{"foo": "bar"}'
    doc.created_at = "2026-01-01T00:00:00+00:00"
    return doc


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis():
    """Non-decode_responses Redis mock (CouncilManager uses bytes)."""
    client = AsyncMock()
    ft_mock = AsyncMock()
    ft_mock.create_index = AsyncMock()
    ft_mock.search = AsyncMock()
    client.ft = MagicMock(return_value=ft_mock)
    client.hset = AsyncMock()
    return client


@pytest.fixture
def mock_embedder():
    emb = AsyncMock()
    emb.embed = AsyncMock(return_value=_fake_vector())
    emb.close = AsyncMock()
    return emb


@pytest.fixture
def manager(mock_redis, mock_embedder):
    mgr = CouncilManager(embedder=mock_embedder)
    mgr._client = mock_redis
    return mgr


# ---------------------------------------------------------------------------
# Tests: Index management
# ---------------------------------------------------------------------------

class TestCouncilManagerIndex:

    @pytest.mark.asyncio
    async def test_ensure_indexes_creates(self, manager, mock_redis):
        await manager._ensure_indexes()
        mock_redis.ft.assert_called_with(INDEX_NAME)
        mock_redis.ft.return_value.create_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_indexes_ignores_existing(self, manager, mock_redis):
        mock_redis.ft.return_value.create_index.side_effect = ResponseError(
            "Index already exists"
        )
        await manager._ensure_indexes()  # should not raise


# ---------------------------------------------------------------------------
# Tests: export_result
# ---------------------------------------------------------------------------

class TestCouncilManagerExport:

    @pytest.mark.asyncio
    async def test_export_stores_hash(self, manager, mock_redis, mock_embedder):
        result = _make_intel_result()
        record = await manager.export_result(result, tags=["crypto"])

        assert isinstance(record, CouncilRecord)
        assert record.query_id == "q-test"
        assert record.merged_text == "merged intel text for testing"
        assert len(record.embedding_vector) == EMBEDDING_DIM
        assert "exa" in record.source_names
        assert "crypto" in record.tags

        # Verify Redis hset was called with correct key prefix
        mock_redis.hset.assert_called_once()
        call_kwargs = mock_redis.hset.call_args
        key = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1].get("name", "")
        # key is first positional arg
        assert key.startswith(PREFIX)

    @pytest.mark.asyncio
    async def test_export_fallback_merged_text(self, manager, mock_redis, mock_embedder):
        """When merged_text is empty, concatenate source snippets."""
        result = _make_intel_result(merged_text="")
        record = await manager.export_result(result)
        assert "snippet text" in record.merged_text

    @pytest.mark.asyncio
    async def test_export_calls_embedder(self, manager, mock_embedder):
        result = _make_intel_result()
        await manager.export_result(result)
        mock_embedder.embed.assert_called_once_with("merged intel text for testing")

    @pytest.mark.asyncio
    async def test_export_metadata_passed_through(self, manager):
        result = _make_intel_result()
        record = await manager.export_result(result, metadata={"source": "test"})
        assert record.metadata == {"source": "test"}


# ---------------------------------------------------------------------------
# Tests: search_keyword
# ---------------------------------------------------------------------------

class TestCouncilManagerKeywordSearch:

    @pytest.mark.asyncio
    async def test_search_keyword_returns_records(self, manager, mock_redis):
        doc = _fake_search_doc()
        mock_result = MagicMock()
        mock_result.docs = [doc]
        mock_redis.ft.return_value.search.return_value = mock_result

        records = await manager.search_keyword("found")
        assert len(records) == 1
        assert records[0].merged_text == "found it"
        assert "exa" in records[0].source_names
        assert "crypto" in records[0].tags

    @pytest.mark.asyncio
    async def test_search_keyword_with_tags(self, manager, mock_redis):
        mock_result = MagicMock()
        mock_result.docs = []
        mock_redis.ft.return_value.search.return_value = mock_result

        await manager.search_keyword("test", tags=["crypto"])
        call_args = mock_redis.ft.return_value.search.call_args
        query_obj = call_args[0][0]
        assert "crypto" in query_obj.get_args()[0]

    @pytest.mark.asyncio
    async def test_search_keyword_error_returns_empty(self, manager, mock_redis):
        mock_redis.ft.return_value.search.side_effect = ResponseError("oops")
        records = await manager.search_keyword("test")
        assert records == []


# ---------------------------------------------------------------------------
# Tests: search_semantic
# ---------------------------------------------------------------------------

class TestCouncilManagerSemanticSearch:

    @pytest.mark.asyncio
    async def test_search_semantic_embeds_query(self, manager, mock_redis, mock_embedder):
        mock_result = MagicMock()
        mock_result.docs = []
        mock_redis.ft.return_value.search.return_value = mock_result

        await manager.search_semantic("find similar")
        mock_embedder.embed.assert_called_once_with("find similar")

    @pytest.mark.asyncio
    async def test_search_semantic_returns_records(self, manager, mock_redis, mock_embedder):
        doc = _fake_search_doc(merged_text="semantic hit")
        mock_result = MagicMock()
        mock_result.docs = [doc]
        mock_redis.ft.return_value.search.return_value = mock_result

        records = await manager.search_semantic("query")
        assert len(records) == 1
        assert records[0].merged_text == "semantic hit"

    @pytest.mark.asyncio
    async def test_search_semantic_passes_vector_blob(self, manager, mock_redis, mock_embedder):
        mock_result = MagicMock()
        mock_result.docs = []
        mock_redis.ft.return_value.search.return_value = mock_result

        await manager.search_semantic("query")
        search_call = mock_redis.ft.return_value.search.call_args
        params = search_call[1].get("query_params", {})
        assert "vec" in params
        # Should be bytes (numpy float32 blob)
        assert isinstance(params["vec"], bytes)
        assert len(params["vec"]) == EMBEDDING_DIM * 4  # float32 = 4 bytes

    @pytest.mark.asyncio
    async def test_search_semantic_error_returns_empty(self, manager, mock_redis, mock_embedder):
        mock_redis.ft.return_value.search.side_effect = ResponseError("vector error")
        records = await manager.search_semantic("query")
        assert records == []


# ---------------------------------------------------------------------------
# Tests: close
# ---------------------------------------------------------------------------

class TestCouncilManagerLifecycle:

    @pytest.mark.asyncio
    async def test_close_disconnects(self, manager, mock_redis, mock_embedder):
        await manager.close()
        mock_redis.aclose.assert_called_once()
        mock_embedder.close.assert_called_once()
        assert manager._client is None


# ---------------------------------------------------------------------------
# Tests: helper
# ---------------------------------------------------------------------------

class TestFloatVectorToBytes:

    def test_roundtrip(self):
        vec = [0.1, 0.2, 0.3]
        blob = _float_vector_to_bytes(vec)
        restored = np.frombuffer(blob, dtype=np.float32).tolist()
        assert len(restored) == 3
        assert abs(restored[0] - 0.1) < 1e-6
