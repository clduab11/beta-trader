"""Integration tests for the Intel pipeline.

Tests the full orchestrator flow with mocked external APIs,
validating the complete pipeline: orchestrator → sources → cache → events.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from intel.cache import RedisCache
from intel.events import get_event_bus, reset_event_bus
from intel.orchestrator import IntelOrchestrator
from intel.sources.exa import ExaSource
from intel.sources.firecrawl import FirecrawlSource
from intel.sources.tavily import TavilySource
from intel.types import IntelDepth, IntelQuery


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


def _make_mock_http_client(responses: dict[str, dict]) -> AsyncMock:
    """Create a mock httpx.AsyncClient with per-endpoint responses."""
    client = AsyncMock()
    client.is_closed = False

    async def _mock_post(url, **kwargs):
        resp = MagicMock(spec=httpx.Response)
        data = responses.get(url, {"status_code": 404, "json": {}})
        resp.status_code = data.get("status_code", 200)
        resp.json.return_value = data.get("json", {})
        resp.text = json.dumps(data.get("json", {}))
        resp.headers = data.get("headers", {})
        return resp

    client.post = _mock_post
    return client


EXA_RESPONSE = {
    "/search": {
        "status_code": 200,
        "json": {
            "results": [
                {
                    "url": "https://example.com/btc-analysis",
                    "title": "Bitcoin Market Analysis",
                    "text": "Bitcoin price is expected to rise based on ETF approval signals.",
                    "score": 0.95,
                },
                {
                    "url": "https://example.com/crypto-news",
                    "title": "Crypto News Daily",
                    "text": "Latest developments in the cryptocurrency market.",
                    "score": 0.88,
                },
                {
                    "url": "https://example.com/etf-update",
                    "title": "ETF Application Update",
                    "text": "SEC reviewing multiple Bitcoin ETF applications.",
                    "score": 0.82,
                },
            ]
        },
    }
}

TAVILY_RESPONSE = {
    "/search": {
        "status_code": 200,
        "json": {
            "results": [
                {
                    "url": "https://news.com/btc-etf",
                    "title": "Breaking: Bitcoin ETF News",
                    "content": "New developments in Bitcoin ETF regulatory landscape.",
                    "score": 0.91,
                },
                {
                    "url": "https://example.com/btc-analysis",  # Duplicate URL
                    "title": "Bitcoin Analysis",
                    "content": "Market analysis from different perspective.",
                    "score": 0.85,
                },
            ]
        },
    }
}

FIRECRAWL_RESPONSE = {
    "/scrape": {
        "status_code": 200,
        "json": {
            "data": {
                "markdown": "# Full Article\n\nDetailed analysis of Bitcoin ETF...",
                "rawHtml": "<html><body>Full article content</body></html>",
                "metadata": {"title": "Full Article", "sourceURL": ""},
            }
        },
    }
}


class TestFullPipelineShallow:
    """Test SHALLOW depth: Exa only."""

    @pytest.mark.asyncio
    async def test_shallow_pipeline(self):
        exa = ExaSource(api_key="test-key")
        exa._client = _make_mock_http_client(EXA_RESPONSE)

        orchestrator = IntelOrchestrator(exa=exa)

        result = await orchestrator.gather_intel("Bitcoin ETF", depth="SHALLOW")

        assert result.depth_used == IntelDepth.SHALLOW
        assert len(result.sources) == 3
        assert all(s.source_name == "exa" for s in result.sources)
        assert result.total_cost_usd > 0
        assert result.latency_ms > 0
        assert result.cached is False
        assert result.merged_text

        await orchestrator.close()


class TestFullPipelineStandard:
    """Test STANDARD depth: Exa + Tavily parallel."""

    @pytest.mark.asyncio
    async def test_standard_pipeline(self):
        exa = ExaSource(api_key="test-key")
        exa._client = _make_mock_http_client(EXA_RESPONSE)

        tavily = TavilySource(api_key="test-key")
        tavily._client = _make_mock_http_client(TAVILY_RESPONSE)

        orchestrator = IntelOrchestrator(exa=exa, tavily=tavily)

        result = await orchestrator.gather_intel("Bitcoin ETF", depth="STANDARD")

        assert result.depth_used == IntelDepth.STANDARD
        # 3 from Exa + 2 from Tavily, but one shared URL → deduplicated
        assert len(result.sources) == 4  # 3 unique Exa + 1 unique Tavily
        source_names = {s.source_name for s in result.sources}
        assert "exa" in source_names
        assert "tavily" in source_names
        assert result.total_cost_usd > 0
        assert result.cached is False

        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_standard_deduplication(self):
        """Results with same URL from different sources are deduplicated."""
        exa = ExaSource(api_key="test-key")
        exa._client = _make_mock_http_client(EXA_RESPONSE)

        tavily = TavilySource(api_key="test-key")
        tavily._client = _make_mock_http_client(TAVILY_RESPONSE)

        orchestrator = IntelOrchestrator(exa=exa, tavily=tavily)

        result = await orchestrator.gather_intel("Bitcoin ETF", depth="STANDARD")

        urls = [s.url for s in result.sources]
        # No duplicate URLs
        assert len(urls) == len(set(urls))

        await orchestrator.close()


class TestFullPipelineDeep:
    """Test DEEP depth: Exa → Firecrawl."""

    @pytest.mark.asyncio
    async def test_deep_pipeline(self):
        exa = ExaSource(api_key="test-key")
        exa._client = _make_mock_http_client(EXA_RESPONSE)

        firecrawl = FirecrawlSource(api_key="test-key")
        firecrawl._client = _make_mock_http_client(FIRECRAWL_RESPONSE)

        orchestrator = IntelOrchestrator(exa=exa, firecrawl=firecrawl)

        result = await orchestrator.gather_intel("Bitcoin ETF analysis", depth="DEEP")

        assert result.depth_used == IntelDepth.DEEP
        assert "exa" in {s.source_name for s in result.sources}
        # Firecrawl scrapes the same URLs as Exa returned, so after dedup the
        # Exa entries (higher relevance) win; verify cost includes scraping
        exa_only_cost = len(EXA_RESPONSE["/search"]["json"]["results"]) * 0.0005
        assert result.total_cost_usd > exa_only_cost  # Firecrawl cost added
        assert result.total_cost_usd > 0

        await orchestrator.close()


class TestEventEmission:
    """Verify events are emitted correctly throughout the pipeline."""

    @pytest.mark.asyncio
    async def test_events_emitted_on_query(self):
        events_received: list[dict] = []

        async def capture_event(event: dict):
            events_received.append(event)

        bus = get_event_bus()
        bus.subscribe("SourceQueried", capture_event)
        bus.subscribe("IntelGathered", capture_event)

        exa = ExaSource(api_key="test-key")
        exa._client = _make_mock_http_client(EXA_RESPONSE)

        orchestrator = IntelOrchestrator(exa=exa)
        await orchestrator.gather_intel("test", depth="SHALLOW")

        # Should have SourceQueried (started + completed) + IntelGathered
        event_types = [e["event_type"] for e in events_received]
        assert "SourceQueried" in event_types
        assert "IntelGathered" in event_types

        # Check IntelGathered payload
        intel_event = next(e for e in events_received if e["event_type"] == "IntelGathered")
        assert "total_cost_usd" in intel_event["payload"]
        assert intel_event["payload"]["cached"] is False

        await orchestrator.close()


class TestCachingIntegration:
    """Test cache hit/miss flows with mocked Redis."""

    @pytest.mark.asyncio
    async def test_cache_stores_and_retrieves(self):
        # Use a real-ish mock for cache behavior
        cache_store: dict[str, str] = {}

        mock_redis = AsyncMock()

        async def mock_get(key):
            return cache_store.get(key)

        async def mock_set(key, value, ex=None):
            cache_store[key] = value

        mock_redis.get = mock_get
        mock_redis.set = mock_set
        mock_redis.ping = AsyncMock()

        cache = RedisCache()
        cache._client = mock_redis

        exa = ExaSource(api_key="test-key")
        exa._client = _make_mock_http_client(EXA_RESPONSE)

        orchestrator = IntelOrchestrator(exa=exa, cache=cache)

        # First query — cache miss
        result1 = await orchestrator.gather_intel("BTC ETF", depth="SHALLOW")
        assert result1.cached is False

        # Second query — cache hit
        result2 = await orchestrator.gather_intel("BTC ETF", depth="SHALLOW")
        assert result2.cached is True
        assert result2.query_id == result1.query_id

        await orchestrator.close()


class TestInputFormats:
    """Test both string and IntelQuery input formats."""

    @pytest.mark.asyncio
    async def test_string_input(self):
        exa = ExaSource(api_key="test-key")
        exa._client = _make_mock_http_client(EXA_RESPONSE)

        orchestrator = IntelOrchestrator(exa=exa)
        result = await orchestrator.gather_intel("simple query", depth="SHALLOW")
        assert result.depth_used == IntelDepth.SHALLOW
        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_intel_query_input(self):
        exa = ExaSource(api_key="test-key")
        exa._client = _make_mock_http_client(EXA_RESPONSE)

        orchestrator = IntelOrchestrator(exa=exa)
        query = IntelQuery(
            query_id="custom-123",
            text="structured query",
            depth=IntelDepth.SHALLOW,
            correlation_id="trace-abc",
        )
        result = await orchestrator.gather_intel(query)
        assert result.query_id == "custom-123"
        assert result.correlation_id == "trace-abc"
        await orchestrator.close()
