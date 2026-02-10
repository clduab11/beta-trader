"""Tests for rate-limit tracking, source rotation, and differentiated retry.

Validates:
- Sources mark themselves rate-limited on RateLimitError
- is_rate_limited returns True during the rate-limit window
- Orchestrator skips rate-limited sources in STANDARD depth
- retry_with_backoff uses 5 attempts for RateLimitError, 3 for APIError
- Tavily per-result cost is proportionally distributed
"""

import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from intel.errors import APIError, RateLimitError
from intel.events import reset_event_bus
from intel.orchestrator import IntelOrchestrator
from intel.retry import (
    API_ERROR_MAX_ATTEMPTS,
    RATE_LIMIT_BASE_DELAY,
    RATE_LIMIT_MAX_ATTEMPTS,
    RATE_LIMIT_MAX_DELAY,
    retry_with_backoff,
)
from intel.sources.exa import COST_PER_RESULT as EXA_COST_PER_RESULT
from intel.sources.exa import ExaSource
from intel.sources.firecrawl import FirecrawlSource
from intel.sources.tavily import COST_PER_SEARCH as TAVILY_COST_PER_SEARCH
from intel.sources.tavily import TavilySource
from intel.types import SearchResult


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


def _make_results(source: str, count: int) -> list[SearchResult]:
    return [
        SearchResult(
            url=f"https://example.com/{source}/{i}",
            title=f"R{i}",
            snippet=f"Snippet {i}",
            relevance_score=0.9,
            source_name=source,
        )
        for i in range(count)
    ]


def _mock_http_client(json_data: dict, status_code: int = 200):
    """Create a mock httpx.AsyncClient that returns a fixed response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = ""
    resp.headers = {"Retry-After": "5"}
    resp.json.return_value = json_data

    client = AsyncMock()
    client.post.return_value = resp
    client.is_closed = False
    return client


# ─── Rate-Limit Tracking Tests ─────────────────────────────────────────────────


class TestRateLimitTracking:
    """Sources mark themselves rate-limited on RateLimitError."""

    @pytest.mark.asyncio
    async def test_exa_marks_rate_limited_on_429(self):
        exa = ExaSource(api_key="test")
        exa._client = _mock_http_client({}, status_code=429)

        assert not exa.is_rate_limited

        with pytest.raises(RateLimitError):
            await exa.search("test")

        assert exa.is_rate_limited

    @pytest.mark.asyncio
    async def test_tavily_marks_rate_limited_on_429(self):
        tavily = TavilySource(api_key="test")
        tavily._client = _mock_http_client({}, status_code=429)

        assert not tavily.is_rate_limited

        with pytest.raises(RateLimitError):
            await tavily.search("test")

        assert tavily.is_rate_limited

    @pytest.mark.asyncio
    async def test_firecrawl_marks_rate_limited_on_429(self):
        firecrawl = FirecrawlSource(api_key="test")
        firecrawl._client = _mock_http_client({}, status_code=429)

        assert not firecrawl.is_rate_limited

        with pytest.raises(RateLimitError):
            await firecrawl.scrape("https://example.com")

        assert firecrawl.is_rate_limited

    @pytest.mark.asyncio
    async def test_rate_limit_expires_after_window(self):
        exa = ExaSource(api_key="test")
        # Manually set a rate-limit that expired 1 second ago
        exa._rate_limited_until = time.monotonic() - 1.0

        assert not exa.is_rate_limited

    @pytest.mark.asyncio
    async def test_api_error_does_not_mark_rate_limited(self):
        exa = ExaSource(api_key="test")
        exa._client = _mock_http_client({}, status_code=500)

        with pytest.raises(APIError):
            await exa.search("test")

        assert not exa.is_rate_limited


# ─── Source Rotation Tests ──────────────────────────────────────────────────────


class TestSourceRotation:
    """Orchestrator skips rate-limited sources in STANDARD depth."""

    @pytest.mark.asyncio
    async def test_standard_skips_rate_limited_exa(self):
        exa = AsyncMock(spec=ExaSource)
        exa.is_rate_limited = True  # Exa is rate-limited
        exa.close = AsyncMock()

        tavily = AsyncMock(spec=TavilySource)
        tavily.search.return_value = _make_results("tavily", 3)
        tavily.is_rate_limited = False
        tavily.close = AsyncMock()

        orch = IntelOrchestrator(exa=exa, tavily=tavily)
        result = await orch.gather_intel("test", depth="STANDARD")

        # Exa should not have been called
        exa.search.assert_not_called()
        # Tavily should have been called
        tavily.search.assert_called_once()
        # Results should come from tavily only
        assert all(s.source_name == "tavily" for s in result.sources)

    @pytest.mark.asyncio
    async def test_standard_skips_rate_limited_tavily(self):
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results("exa", 10)
        exa.is_rate_limited = False
        exa.close = AsyncMock()

        tavily = AsyncMock(spec=TavilySource)
        tavily.is_rate_limited = True  # Tavily is rate-limited
        tavily.close = AsyncMock()

        orch = IntelOrchestrator(exa=exa, tavily=tavily)
        result = await orch.gather_intel("test", depth="STANDARD")

        tavily.search.assert_not_called()
        exa.search.assert_called_once()
        assert all(s.source_name == "exa" for s in result.sources)

    @pytest.mark.asyncio
    async def test_standard_both_rate_limited_returns_empty(self):
        exa = AsyncMock(spec=ExaSource)
        exa.is_rate_limited = True
        exa.close = AsyncMock()

        tavily = AsyncMock(spec=TavilySource)
        tavily.is_rate_limited = True
        tavily.close = AsyncMock()

        orch = IntelOrchestrator(exa=exa, tavily=tavily)
        result = await orch.gather_intel("test", depth="STANDARD")

        exa.search.assert_not_called()
        tavily.search.assert_not_called()
        assert len(result.sources) == 0


# ─── Differentiated Retry Tests ────────────────────────────────────────────────


class TestDifferentiatedRetry:
    """retry_with_backoff uses separate attempt budgets per error type."""

    @pytest.mark.asyncio
    async def test_api_error_exhausts_3_attempts(self):
        fn = AsyncMock(side_effect=APIError("fail", service_name="test"))
        with pytest.raises(APIError):
            await retry_with_backoff(fn, max_attempts=3, base_delay=0.001)
        assert fn.call_count == API_ERROR_MAX_ATTEMPTS

    @pytest.mark.asyncio
    async def test_rate_limit_error_exhausts_5_attempts(self):
        fn = AsyncMock(side_effect=RateLimitError("limited", service_name="test"))
        with pytest.raises(RateLimitError):
            await retry_with_backoff(
                fn,
                max_attempts=3,
                base_delay=0.001,
                rate_limit_max_attempts=5,
                rate_limit_base_delay=0.001,
                rate_limit_max_delay=0.01,
            )
        assert fn.call_count == RATE_LIMIT_MAX_ATTEMPTS

    @pytest.mark.asyncio
    async def test_rate_limit_recovers_within_5_attempts(self):
        fn = AsyncMock(
            side_effect=[
                RateLimitError("limited", service_name="test"),
                RateLimitError("limited", service_name="test"),
                RateLimitError("limited", service_name="test"),
                RateLimitError("limited", service_name="test"),
                "ok",
            ]
        )
        result = await retry_with_backoff(
            fn,
            max_attempts=3,
            base_delay=0.001,
            rate_limit_max_attempts=5,
            rate_limit_base_delay=0.001,
            rate_limit_max_delay=0.01,
        )
        assert result == "ok"
        assert fn.call_count == 5

    @pytest.mark.asyncio
    async def test_constants_match_spec(self):
        assert API_ERROR_MAX_ATTEMPTS == 3
        assert RATE_LIMIT_MAX_ATTEMPTS == 5
        assert RATE_LIMIT_BASE_DELAY == 2.0
        assert RATE_LIMIT_MAX_DELAY == 32.0


# ─── Tavily Per-Result Cost Tests ──────────────────────────────────────────────


class TestTavilyPerResultCost:
    """Tavily results carry proportional cost, not full per-search cost each."""

    @pytest.mark.asyncio
    async def test_tavily_per_result_cost_is_proportional(self):
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results("exa", 5)
        exa.is_rate_limited = False
        exa.close = AsyncMock()

        tavily = AsyncMock(spec=TavilySource)
        tavily.search.return_value = _make_results("tavily", 5)
        tavily.is_rate_limited = False
        tavily.close = AsyncMock()

        orch = IntelOrchestrator(exa=exa, tavily=tavily)
        result = await orch.gather_intel("test", depth="STANDARD")

        tavily_sources = [s for s in result.sources if s.source_name == "tavily"]
        for src in tavily_sources:
            expected_per_result = TAVILY_COST_PER_SEARCH / 5
            assert abs(src.cost_usd - expected_per_result) < 1e-9

    @pytest.mark.asyncio
    async def test_exa_per_result_cost_unchanged(self):
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results("exa", 5)
        exa.is_rate_limited = False
        exa.close = AsyncMock()

        orch = IntelOrchestrator(exa=exa)
        result = await orch.gather_intel("test", depth="SHALLOW")

        for src in result.sources:
            assert src.cost_usd == EXA_COST_PER_RESULT

    @pytest.mark.asyncio
    async def test_tavily_total_cost_still_correct(self):
        """Sum of all per-result costs for Tavily equals the flat per-search fee."""
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results("exa", 10)
        exa.is_rate_limited = False
        exa.close = AsyncMock()

        tavily = AsyncMock(spec=TavilySource)
        tavily.search.return_value = _make_results("tavily", 5)
        tavily.is_rate_limited = False
        tavily.close = AsyncMock()

        orch = IntelOrchestrator(exa=exa, tavily=tavily)
        result = await orch.gather_intel("test", depth="STANDARD")

        tavily_sources = [s for s in result.sources if s.source_name == "tavily"]
        tavily_sum = sum(s.cost_usd for s in tavily_sources)
        assert abs(tavily_sum - TAVILY_COST_PER_SEARCH) < 1e-9
