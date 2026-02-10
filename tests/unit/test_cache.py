"""Unit tests for Redis cache wrapper."""

from unittest.mock import AsyncMock

import pytest

from intel.cache import RedisCache
from intel.types import IntelDepth, IntelResult


class TestRedisCacheMakeKey:
    def test_key_format(self):
        key = RedisCache.make_key("test query", "STANDARD")
        assert key.startswith("intel:cache:")
        assert len(key) > len("intel:cache:")

    def test_deterministic(self):
        key1 = RedisCache.make_key("same query", "STANDARD")
        key2 = RedisCache.make_key("same query", "STANDARD")
        assert key1 == key2

    def test_different_queries(self):
        key1 = RedisCache.make_key("query A", "STANDARD")
        key2 = RedisCache.make_key("query B", "STANDARD")
        assert key1 != key2

    def test_different_depths(self):
        key1 = RedisCache.make_key("same query", "SHALLOW")
        key2 = RedisCache.make_key("same query", "DEEP")
        assert key1 != key2


class TestRedisCache:
    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        mock.delete = AsyncMock(return_value=1)
        mock.ping = AsyncMock()
        return mock

    @pytest.fixture
    def cache(self, mock_redis):
        """Create a RedisCache with mocked client."""
        c = RedisCache()
        c._client = mock_redis
        return c

    @pytest.mark.asyncio
    async def test_get_miss(self, cache, mock_redis):
        mock_redis.get.return_value = None
        result = await cache.get("intel:cache:abc")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_hit(self, cache, mock_redis):
        intel_result = IntelResult(
            query_id="q1",
            correlation_id="c1",
            depth_used=IntelDepth.STANDARD,
            total_cost_usd=0.01,
        )
        mock_redis.get.return_value = intel_result.model_dump_json()

        result = await cache.get("intel:cache:abc")
        assert result is not None
        assert result.query_id == "q1"
        assert result.cached is True

    @pytest.mark.asyncio
    async def test_set(self, cache, mock_redis):
        intel_result = IntelResult(
            query_id="q1",
            correlation_id="c1",
            depth_used=IntelDepth.STANDARD,
        )
        await cache.set("intel:cache:abc", intel_result, ttl=1800)
        mock_redis.set.assert_called_once()
        call_kwargs = mock_redis.set.call_args
        assert call_kwargs[1]["ex"] == 1800

    @pytest.mark.asyncio
    async def test_delete(self, cache, mock_redis):
        result = await cache.delete("intel:cache:abc")
        assert result is True
        mock_redis.delete.assert_called_once_with("intel:cache:abc")

    @pytest.mark.asyncio
    async def test_health_check_ok(self, cache, mock_redis):
        assert await cache.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_fail(self, cache, mock_redis):
        mock_redis.ping.side_effect = ConnectionError("refused")
        assert await cache.health_check() is False

    @pytest.mark.asyncio
    async def test_get_error_returns_none(self, cache, mock_redis):
        mock_redis.get.side_effect = Exception("connection error")
        result = await cache.get("intel:cache:abc")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_error_does_not_raise(self, cache, mock_redis):
        mock_redis.set.side_effect = Exception("connection error")
        intel_result = IntelResult(
            query_id="q1",
            correlation_id="c1",
            depth_used=IntelDepth.STANDARD,
        )
        # Should not raise
        await cache.set("intel:cache:abc", intel_result)
