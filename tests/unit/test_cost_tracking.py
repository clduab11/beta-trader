"""Cost tracking accuracy tests (±$0.001).

Validates that the IntelOrchestrator calculates costs correctly
for each depth level per ticket acceptance criteria.
"""

from unittest.mock import AsyncMock

import pytest

from intel.events import reset_event_bus
from intel.orchestrator import IntelOrchestrator
from intel.sources.exa import COST_PER_RESULT as EXA_COST_PER_RESULT
from intel.sources.exa import ExaSource
from intel.sources.firecrawl import COST_PER_PAGE, FirecrawlSource
from intel.sources.tavily import COST_PER_SEARCH as TAVILY_COST_PER_SEARCH
from intel.sources.tavily import TavilySource
from intel.types import ScrapedContent, SearchResult

COST_TOLERANCE = 0.001


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


class TestShallowCost:
    """SHALLOW: Exa only, 5 results → cost = 5 × $0.0005 = $0.0025."""

    @pytest.mark.asyncio
    async def test_shallow_exact_cost(self):
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results("exa", 5)
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa)
        result = await orchestrator.gather_intel("test", depth="SHALLOW")

        expected = 5 * EXA_COST_PER_RESULT  # $0.0025
        assert abs(result.total_cost_usd - expected) < COST_TOLERANCE

    @pytest.mark.asyncio
    async def test_shallow_zero_results_zero_cost(self):
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = []
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa)
        result = await orchestrator.gather_intel("test", depth="SHALLOW")

        assert result.total_cost_usd == 0.0


class TestStandardCost:
    """STANDARD: Exa (10 results) + Tavily (1 search) → cost = 10 × $0.0005 + $0.01."""

    @pytest.mark.asyncio
    async def test_standard_exact_cost(self):
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results("exa", 10)
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        tavily = AsyncMock(spec=TavilySource)
        tavily.search.return_value = _make_results("tavily", 5)
        tavily.close = AsyncMock()
        tavily.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa, tavily=tavily)
        result = await orchestrator.gather_intel("test", depth="STANDARD")

        expected = (10 * EXA_COST_PER_RESULT) + TAVILY_COST_PER_SEARCH  # $0.005 + $0.01
        assert abs(result.total_cost_usd - expected) < COST_TOLERANCE

    @pytest.mark.asyncio
    async def test_standard_exa_only_when_tavily_fails(self):
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = _make_results("exa", 10)
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        tavily = AsyncMock(spec=TavilySource)
        tavily.search.side_effect = Exception("Tavily down")
        tavily.close = AsyncMock()
        tavily.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa, tavily=tavily)
        result = await orchestrator.gather_intel("test", depth="STANDARD")

        # Only Exa cost — no Tavily cost since it failed
        expected = 10 * EXA_COST_PER_RESULT  # $0.005
        assert abs(result.total_cost_usd - expected) < COST_TOLERANCE


class TestDeepCost:
    """DEEP: Exa (10) + Firecrawl (N pages) → cost includes scraping."""

    @pytest.mark.asyncio
    async def test_deep_cost_includes_scraping(self):
        exa_results = _make_results("exa", 10)
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = exa_results
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        scraped = [
            ScrapedContent(url=f"https://example.com/exa/{i}", title=f"S{i}", markdown="content")
            for i in range(3)  # 3 pages scraped
        ]
        firecrawl = AsyncMock(spec=FirecrawlSource)
        firecrawl.batch_scrape.return_value = scraped
        firecrawl.close = AsyncMock()
        firecrawl.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa, firecrawl=firecrawl)
        result = await orchestrator.gather_intel("test deep query", depth="DEEP")

        exa_cost = 10 * EXA_COST_PER_RESULT
        firecrawl_cost = 3 * COST_PER_PAGE
        expected = exa_cost + firecrawl_cost
        assert abs(result.total_cost_usd - expected) < COST_TOLERANCE

    @pytest.mark.asyncio
    async def test_deep_no_scrape_urls_no_firecrawl_cost(self):
        """When Exa returns no scrapable URLs, Firecrawl cost is 0."""
        # Results with social media URLs (filtered out by _extract_scrape_urls)
        exa_results = [
            SearchResult(
                url="https://twitter.com/post/1",
                title="Tweet",
                snippet="Social post",
                relevance_score=0.8,
                source_name="exa",
            )
        ]
        exa = AsyncMock(spec=ExaSource)
        exa.search.return_value = exa_results
        exa.close = AsyncMock()
        exa.is_rate_limited = False

        firecrawl = AsyncMock(spec=FirecrawlSource)
        firecrawl.batch_scrape.return_value = []
        firecrawl.close = AsyncMock()
        firecrawl.is_rate_limited = False

        orchestrator = IntelOrchestrator(exa=exa, firecrawl=firecrawl)
        result = await orchestrator.gather_intel("test", depth="DEEP")

        expected = 1 * EXA_COST_PER_RESULT  # Only Exa cost
        assert abs(result.total_cost_usd - expected) < COST_TOLERANCE


class TestCostConstants:
    """Verify cost constants match documented API pricing."""

    def test_exa_cost_per_result(self):
        assert EXA_COST_PER_RESULT == 0.0005

    def test_tavily_cost_per_search(self):
        assert TAVILY_COST_PER_SEARCH == 0.01

    def test_firecrawl_cost_per_page(self):
        assert COST_PER_PAGE == 0.001
