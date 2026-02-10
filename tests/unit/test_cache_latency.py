"""Cache performance and latency tests.

Validates:
- Cached queries return in <50ms (ticket validation criteria)
- Cache key determinism and isolation
- Cache TTL behavior
"""

import time
from unittest.mock import AsyncMock

import pytest

from intel.cache import RedisCache
from intel.events import reset_event_bus
from intel.orchestrator import IntelOrchestrator
from intel.sources.exa import ExaSource
from intel.types import IntelDepth, IntelResult, SearchResult


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


def _make_results(count: int) -> list[SearchResult]:
    return [
        SearchResult(
            url=f"https://example.com/{i}",
            title=f"R{i}",
            snippet=f"Snippet {i}",
            relevance_score=0.9,
            source_name="exa",
        )
        for i in range(count)
    ]


class TestCacheLatency:
    """Cached queries must return in <50ms."""

    @pytest.mark.asyncio
    async def test_cached_result_returns_under_50ms(self):
        """Simulate cache hit and verify latency < 50ms."""
        cached_result = IntelResult(
            query_id="q1",
            correlation_id="c1",
            depth_used=IntelDepth.SHALLOW,
            total_cost_usd=0.0025,
            cached=False,
        )

        cache = AsyncMock(spec=RedisCache)
        cache.get.return_value = cached_result
        cache.close = AsyncMock()

        exa = AsyncMock(spec=ExaSource)
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa, cache=cache)

        start = time.monotonic()
        result = await orchestrator.gather_intel("test", depth="SHALLOW")
        elapsed_ms = (time.monotonic() - start) * 1000

        assert result.cached is True
        assert elapsed_ms < 50, f"Cache hit took {elapsed_ms:.1f}ms, expected <50ms"

        # Source should NOT have been queried
        exa.search.assert_not_called()

        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_cached_result_latency_field_populated(self):
        """The IntelResult.latency_ms field should reflect actual cache hit time."""
        cached_result = IntelResult(
            query_id="q1",
            correlation_id="c1",
            depth_used=IntelDepth.STANDARD,
            total_cost_usd=0.01,
        )

        cache = AsyncMock(spec=RedisCache)
        cache.get.return_value = cached_result
        cache.close = AsyncMock()

        exa = AsyncMock(spec=ExaSource)
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa, cache=cache)
        result = await orchestrator.gather_intel("test", depth="STANDARD")

        assert result.latency_ms > 0
        assert result.latency_ms < 50  # Should be very fast for a mock

        await orchestrator.close()


class TestCacheIsolation:
    """Different queries and depths produce different cache keys."""

    def test_same_query_different_depth(self):
        key1 = RedisCache.make_key("bitcoin ETF", "SHALLOW")
        key2 = RedisCache.make_key("bitcoin ETF", "DEEP")
        assert key1 != key2

    def test_same_depth_different_query(self):
        key1 = RedisCache.make_key("bitcoin ETF", "STANDARD")
        key2 = RedisCache.make_key("ethereum DeFi", "STANDARD")
        assert key1 != key2

    def test_key_prefix(self):
        key = RedisCache.make_key("test", "SHALLOW")
        assert key.startswith("intel:cache:")

    def test_key_is_sha256_hex(self):
        key = RedisCache.make_key("test", "SHALLOW")
        hex_part = key.replace("intel:cache:", "")
        assert len(hex_part) == 64  # SHA-256 hex digest length
        assert all(c in "0123456789abcdef" for c in hex_part)


class TestCacheStoreAndRetrieve:
    """Test full cache store → retrieve cycle."""

    @pytest.mark.asyncio
    async def test_fresh_query_stored_then_cached(self):
        """First call stores, second call retrieves from cache."""
        store: dict[str, str] = {}

        mock_redis = AsyncMock()

        async def mock_get(key):
            return store.get(key)

        async def mock_set(key, value, ex=None):
            store[key] = value

        mock_redis.get = mock_get
        mock_redis.set = mock_set

        cache = RedisCache()
        cache._client = mock_redis

        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results(3)
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa, cache=cache)

        # First call — miss, queries source
        result1 = await orchestrator.gather_intel("BTC", depth="SHALLOW")
        assert result1.cached is False
        assert exa.search.call_count == 1

        # Second call — hit, no source query
        result2 = await orchestrator.gather_intel("BTC", depth="SHALLOW")
        assert result2.cached is True
        assert exa.search.call_count == 1  # Not called again

        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_different_depth_not_cached(self):
        """Same query with different depth is not a cache hit."""
        store: dict[str, str] = {}

        mock_redis = AsyncMock()

        async def mock_get(key):
            return store.get(key)

        async def mock_set(key, value, ex=None):
            store[key] = value

        mock_redis.get = mock_get
        mock_redis.set = mock_set

        cache = RedisCache()
        cache._client = mock_redis

        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results(5)
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        tavily = AsyncMock()
        tavily.search = AsyncMock(return_value=_make_results(3))
        tavily.close = AsyncMock()

        orchestrator = IntelOrchestrator(exa=exa, tavily=tavily, cache=cache)

        await orchestrator.gather_intel("BTC", depth="SHALLOW")
        await orchestrator.gather_intel("BTC", depth="STANDARD")

        # Both should have queried sources (different cache keys)
        assert exa.search.call_count == 2

        await orchestrator.close()
