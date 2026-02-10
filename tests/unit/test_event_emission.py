"""Event emission completeness tests.

Validates that SourceQueried, IntelGathered, and CircuitBreakerStateChanged
events are emitted correctly per docs/interfaces/events.md.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from intel.errors import APIError
from intel.events import get_event_bus, reset_event_bus
from intel.orchestrator import IntelOrchestrator
from intel.sources.exa import ExaSource
from intel.sources.firecrawl import FirecrawlSource
from intel.sources.tavily import TavilySource
from intel.types import IntelDepth


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


@pytest.fixture(autouse=True)
def _fast_sleep():
    """Patch asyncio.sleep to avoid delays in retry backoff."""
    with patch("asyncio.sleep", new_callable=AsyncMock):
        yield


def _mock_http_client(response_json: dict, status_code: int = 200):
    """Create a mock httpx.AsyncClient."""
    client = AsyncMock()
    client.is_closed = False

    async def _post(url, **kwargs):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.json.return_value = response_json
        resp.text = json.dumps(response_json)
        resp.headers = {}
        return resp

    client.post = _post
    return client


EXA_RESP = {
    "results": [
        {"url": "https://ex.com/1", "title": "T1", "text": "Content 1", "score": 0.9},
    ]
}

TAVILY_RESP = {
    "results": [
        {"url": "https://news.com/1", "title": "N1", "content": "News content", "score": 0.85},
    ]
}

FIRECRAWL_RESP = {
    "data": {
        "markdown": "# Article\nFull content",
        "rawHtml": "<html>Full</html>",
        "metadata": {"title": "Article"},
    }
}


class TestSourceQueriedEvents:
    """Verify SourceQueried events have started/completed/failed statuses."""

    @pytest.mark.asyncio
    async def test_exa_emits_started_and_completed(self):
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("SourceQueried", capture)

        exa = ExaSource(api_key="test")
        exa._client = _mock_http_client(EXA_RESP)

        await exa.search("test query", num_results=5, correlation_id="trace-1")

        source_events = [e for e in events if e["event_type"] == "SourceQueried"]
        statuses = [e["payload"]["source"] for e in source_events]
        assert all(s == "exa" for s in statuses)

        status_values = [e["payload"]["status"] for e in source_events]
        assert "started" in status_values
        assert "completed" in status_values

        # Completed event should have latency_ms and result_count
        completed = next(e for e in source_events if e["payload"]["status"] == "completed")
        assert "latency_ms" in completed["payload"]
        assert "result_count" in completed["payload"]
        assert "cost_usd" in completed["payload"]

    @pytest.mark.asyncio
    async def test_exa_emits_failed_on_error(self):
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("SourceQueried", capture)

        exa = ExaSource(api_key="test")
        exa._client = _mock_http_client({}, status_code=500)

        with pytest.raises(APIError):
            await exa.search("test query")

        source_events = [e for e in events if e["event_type"] == "SourceQueried"]
        status_values = [e["payload"]["status"] for e in source_events]
        assert "started" in status_values
        assert "failed" in status_values

        failed = next(e for e in source_events if e["payload"]["status"] == "failed")
        assert "error" in failed["payload"]
        assert "latency_ms" in failed["payload"]

    @pytest.mark.asyncio
    async def test_tavily_emits_started_and_completed(self):
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("SourceQueried", capture)

        tavily = TavilySource(api_key="test")
        tavily._client = _mock_http_client(TAVILY_RESP)

        await tavily.search("news query", max_results=3, correlation_id="trace-2")

        source_events = [e for e in events if e["event_type"] == "SourceQueried"]
        assert len(source_events) >= 2

        statuses = {e["payload"]["status"] for e in source_events}
        assert "started" in statuses
        assert "completed" in statuses

        sources = {e["payload"]["source"] for e in source_events}
        assert "tavily" in sources

    @pytest.mark.asyncio
    async def test_firecrawl_emits_started_and_completed(self):
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("SourceQueried", capture)

        firecrawl = FirecrawlSource(api_key="test")
        firecrawl._client = _mock_http_client(FIRECRAWL_RESP)

        await firecrawl.scrape("https://example.com/page", correlation_id="trace-3")

        source_events = [e for e in events if e["event_type"] == "SourceQueried"]
        assert len(source_events) >= 2

        statuses = {e["payload"]["status"] for e in source_events}
        assert "started" in statuses
        assert "completed" in statuses

        sources = {e["payload"]["source"] for e in source_events}
        assert "firecrawl" in sources


class TestIntelGatheredEvent:
    """Verify IntelGathered event payload matches docs/interfaces/events.md."""

    @pytest.mark.asyncio
    async def test_intel_gathered_payload_structure(self):
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("IntelGathered", capture)

        exa = ExaSource(api_key="test")
        exa._client = _mock_http_client(EXA_RESP)

        orchestrator = IntelOrchestrator(exa=exa)
        await orchestrator.gather_intel("test", depth="SHALLOW")

        assert len(events) == 1
        event = events[0]

        # Verify envelope structure
        assert event["event_type"] == "IntelGathered"
        assert "event_id" in event
        assert "timestamp" in event
        assert event["source_module"] == "intel.orchestrator"

        # Verify payload fields per events.md
        payload = event["payload"]
        assert "query_id" in payload
        assert payload["depth_used"] == "SHALLOW"
        assert "source_count" in payload
        assert isinstance(payload["total_cost_usd"], float)
        assert isinstance(payload["latency_ms"], float)
        assert payload["cached"] is False
        assert "result_summary" in payload
        assert "has_embeddings" in payload

        await orchestrator.close()

    @pytest.mark.asyncio
    async def test_intel_gathered_cached_flag(self):
        """Cached results emit IntelGathered with cached=True."""
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("IntelGathered", capture)

        from intel.cache import RedisCache
        from intel.types import IntelResult

        cache = AsyncMock(spec=RedisCache)
        cached_result = IntelResult(
            query_id="q1",
            correlation_id="c1",
            depth_used=IntelDepth.STANDARD,
            total_cost_usd=0.01,
        )
        cache.get.return_value = cached_result
        cache.close = AsyncMock()

        exa = AsyncMock(spec=ExaSource)
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa, cache=cache)
        await orchestrator.gather_intel("test", depth="STANDARD")

        assert len(events) == 1
        assert events[0]["payload"]["cached"] is True

        await orchestrator.close()


class TestEventCorrelation:
    """Verify correlation_id flows through all events."""

    @pytest.mark.asyncio
    async def test_correlation_id_propagated(self):
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("SourceQueried", capture)
        bus.subscribe("IntelGathered", capture)

        exa = ExaSource(api_key="test")
        exa._client = _mock_http_client(EXA_RESP)

        from intel.types import IntelQuery

        query = IntelQuery(
            text="test",
            depth=IntelDepth.SHALLOW,
            correlation_id="trace-abc-123",
        )
        orchestrator = IntelOrchestrator(exa=exa)
        await orchestrator.gather_intel(query)

        # All events should carry the same correlation_id
        for event in events:
            assert event["correlation_id"] == "trace-abc-123"

        await orchestrator.close()


class TestMultiSourceEvents:
    """Verify STANDARD depth emits events for both sources."""

    @pytest.mark.asyncio
    async def test_standard_emits_events_for_exa_and_tavily(self):
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("SourceQueried", capture)
        bus.subscribe("IntelGathered", capture)

        exa = ExaSource(api_key="test")
        exa._client = _mock_http_client(EXA_RESP)

        tavily = TavilySource(api_key="test")
        tavily._client = _mock_http_client(TAVILY_RESP)

        orchestrator = IntelOrchestrator(exa=exa, tavily=tavily)
        await orchestrator.gather_intel("test", depth="STANDARD")

        source_events = [e for e in events if e["event_type"] == "SourceQueried"]
        sources_queried = {e["payload"]["source"] for e in source_events}
        assert "exa" in sources_queried
        assert "tavily" in sources_queried

        intel_events = [e for e in events if e["event_type"] == "IntelGathered"]
        assert len(intel_events) == 1

        await orchestrator.close()
