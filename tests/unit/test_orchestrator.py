"""Unit tests for the IntelOrchestrator."""

from unittest.mock import AsyncMock

import pytest

from intel.cache import RedisCache
from intel.events import reset_event_bus
from intel.orchestrator import IntelOrchestrator
from intel.sources.exa import ExaSource
from intel.sources.firecrawl import FirecrawlSource
from intel.sources.tavily import TavilySource
from intel.types import (
    IntelDepth,
    IntelQuery,
    IntelResult,
    IntelSource,
    ScrapedContent,
    SearchResult,
)


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


def _make_search_results(source: str, count: int) -> list[SearchResult]:
    """Helper to create mock search results."""
    return [
        SearchResult(
            url=f"https://example.com/{source}/{i}",
            title=f"{source} Result {i}",
            snippet=f"Content from {source} about topic {i}",
            relevance_score=0.9 - (i * 0.05),
            source_name=source,
        )
        for i in range(count)
    ]


def _make_scraped_content(url: str) -> ScrapedContent:
    """Helper to create mock scraped content."""
    return ScrapedContent(
        url=url,
        title=f"Scraped: {url}",
        content=f"<html>Full content from {url}</html>",
        markdown=f"# Scraped Content\n\nFull text from {url}",
    )


@pytest.fixture
def mock_exa():
    exa = AsyncMock(spec=ExaSource)
    exa.search.return_value = _make_search_results("exa", 5)
    exa.close = AsyncMock()
    exa.is_rate_limited = False
    return exa


@pytest.fixture
def mock_tavily():
    tavily = AsyncMock(spec=TavilySource)
    tavily.search.return_value = _make_search_results("tavily", 3)
    tavily.close = AsyncMock()
    tavily.is_rate_limited = False
    return tavily


@pytest.fixture
def mock_firecrawl():
    firecrawl = AsyncMock(spec=FirecrawlSource)
    firecrawl.batch_scrape.return_value = [
        _make_scraped_content("https://scraped.example.com/page-0"),
        _make_scraped_content("https://scraped.example.com/page-1"),
    ]
    firecrawl.close = AsyncMock()
    firecrawl.is_rate_limited = False
    return firecrawl


@pytest.fixture
def mock_cache():
    cache = AsyncMock(spec=RedisCache)
    cache.get.return_value = None
    cache.set = AsyncMock()
    cache.close = AsyncMock()
    return cache


@pytest.fixture
def orchestrator(mock_exa, mock_tavily, mock_firecrawl, mock_cache):
    return IntelOrchestrator(
        exa=mock_exa,
        tavily=mock_tavily,
        firecrawl=mock_firecrawl,
        cache=mock_cache,
    )


class TestIntelOrchestratorShallow:
    @pytest.mark.asyncio
    async def test_shallow_queries_exa_only(self, orchestrator, mock_exa, mock_tavily):
        result = await orchestrator.gather_intel("test query", depth="SHALLOW")

        assert result.depth_used == IntelDepth.SHALLOW
        mock_exa.search.assert_called_once()
        mock_tavily.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_shallow_returns_5_results(self, orchestrator, mock_exa):
        mock_exa.search.return_value = _make_search_results("exa", 5)
        result = await orchestrator.gather_intel("test", depth="SHALLOW")
        assert len(result.sources) == 5

    @pytest.mark.asyncio
    async def test_shallow_cost_tracking(self, orchestrator):
        result = await orchestrator.gather_intel("test", depth="SHALLOW")
        assert result.total_cost_usd > 0


class TestIntelOrchestratorStandard:
    @pytest.mark.asyncio
    async def test_standard_queries_exa_and_tavily(
        self, orchestrator, mock_exa, mock_tavily
    ):
        result = await orchestrator.gather_intel("test query", depth="STANDARD")

        assert result.depth_used == IntelDepth.STANDARD
        mock_exa.search.assert_called_once()
        mock_tavily.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_standard_merges_results(self, orchestrator):
        result = await orchestrator.gather_intel("test", depth="STANDARD")
        source_names = {s.source_name for s in result.sources}
        assert "exa" in source_names
        assert "tavily" in source_names

    @pytest.mark.asyncio
    async def test_standard_deduplicates_by_url(self, orchestrator, mock_exa, mock_tavily):
        # Both sources return results with the same URL
        mock_exa.search.return_value = [
            SearchResult(
                url="https://shared.com/article",
                title="Article",
                snippet="From Exa",
                relevance_score=0.9,
                source_name="exa",
            )
        ]
        mock_tavily.search.return_value = [
            SearchResult(
                url="https://shared.com/article",
                title="Article",
                snippet="From Tavily",
                relevance_score=0.8,
                source_name="tavily",
            )
        ]

        result = await orchestrator.gather_intel("test", depth="STANDARD")
        # Should keep the higher-scored version only
        assert len(result.sources) == 1
        assert result.sources[0].relevance_score == 0.9

    @pytest.mark.asyncio
    async def test_standard_partial_failure(self, orchestrator, mock_exa, mock_tavily):
        """If Tavily fails, still returns Exa results."""
        mock_tavily.search.side_effect = Exception("Tavily down")

        result = await orchestrator.gather_intel("test", depth="STANDARD")
        assert len(result.sources) > 0
        assert all(s.source_name == "exa" for s in result.sources)


class TestIntelOrchestratorDeep:
    @pytest.mark.asyncio
    async def test_deep_includes_firecrawl(
        self, orchestrator, mock_exa, mock_firecrawl
    ):
        result = await orchestrator.gather_intel("test query", depth="DEEP")

        assert result.depth_used == IntelDepth.DEEP
        mock_exa.search.assert_called_once()
        mock_firecrawl.batch_scrape.assert_called_once()

    @pytest.mark.asyncio
    async def test_deep_includes_scraped_sources(self, orchestrator):
        result = await orchestrator.gather_intel("test", depth="DEEP")
        source_names = {s.source_name for s in result.sources}
        assert "firecrawl" in source_names

    @pytest.mark.asyncio
    async def test_deep_cost_includes_scraping(self, orchestrator):
        result = await orchestrator.gather_intel("test", depth="DEEP")
        assert result.total_cost_usd > 0


class TestIntelOrchestratorCaching:
    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(self, orchestrator, mock_cache, mock_exa):
        cached_result = IntelResult(
            query_id="cached-q",
            correlation_id="cached-c",
            depth_used=IntelDepth.STANDARD,
            total_cost_usd=0.01,
            cached=False,
        )
        mock_cache.get.return_value = cached_result

        result = await orchestrator.gather_intel("test", depth="STANDARD")

        assert result.cached is True
        mock_exa.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_queries_sources(self, orchestrator, mock_cache, mock_exa):
        mock_cache.get.return_value = None

        await orchestrator.gather_intel("test", depth="SHALLOW")

        mock_exa.search.assert_called_once()
        mock_cache.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_custom_cache_ttl(self, orchestrator, mock_cache):
        query = IntelQuery(text="test", depth=IntelDepth.SHALLOW, cache_ttl_seconds=600)
        await orchestrator.gather_intel(query)

        # Verify cache.set was called with custom TTL
        set_call = mock_cache.set.call_args
        assert set_call[1]["ttl"] == 600


class TestIntelOrchestratorInput:
    @pytest.mark.asyncio
    async def test_string_query(self, orchestrator):
        result = await orchestrator.gather_intel("simple string query", depth="SHALLOW")
        assert result.query_id  # Auto-generated

    @pytest.mark.asyncio
    async def test_intel_query_object(self, orchestrator):
        query = IntelQuery(
            query_id="custom-id",
            text="structured query",
            depth=IntelDepth.DEEP,
            correlation_id="trace-123",
        )
        result = await orchestrator.gather_intel(query)
        assert result.query_id == "custom-id"
        assert result.correlation_id == "trace-123"


class TestIntelOrchestratorMerging:
    def test_merge_snippets(self):
        sources = [
            IntelSource(source_name="exa", title="Article 1", snippet="First snippet"),
            IntelSource(source_name="tavily", title="Article 2", snippet="Second snippet"),
        ]
        merged = IntelOrchestrator._merge_snippets(sources)
        assert "First snippet" in merged
        assert "Second snippet" in merged
        assert "[exa]" in merged
        assert "[tavily]" in merged

    def test_deduplicate_sources(self):
        sources = [
            IntelSource(
                source_name="exa",
                url="https://same.com",
                title="A",
                snippet="S",
                relevance_score=0.9,
            ),
            IntelSource(
                source_name="tavily",
                url="https://same.com",
                title="A",
                snippet="S",
                relevance_score=0.7,
            ),
            IntelSource(
                source_name="exa",
                url="https://unique.com",
                title="B",
                snippet="S2",
                relevance_score=0.8,
            ),
        ]
        deduped = IntelOrchestrator._deduplicate_sources(sources)
        assert len(deduped) == 2
        # Higher score should win
        urls = {s.url for s in deduped}
        assert "https://same.com" in urls
        assert "https://unique.com" in urls

    def test_extract_scrape_urls_skips_social(self):
        results = [
            SearchResult(url="https://example.com/good", title="Good"),
            SearchResult(url="https://twitter.com/bad", title="Bad"),
            SearchResult(url="https://reddit.com/bad", title="Bad"),
            SearchResult(url="https://news.com/good2", title="Good2"),
        ]
        urls = IntelOrchestrator._extract_scrape_urls(results)
        assert "https://example.com/good" in urls
        assert "https://news.com/good2" in urls
        assert not any("twitter" in u for u in urls)
        assert not any("reddit" in u for u in urls)

    def test_extract_scrape_urls_max_limit(self):
        results = [
            SearchResult(url=f"https://example.com/{i}", title=f"R{i}")
            for i in range(20)
        ]
        urls = IntelOrchestrator._extract_scrape_urls(results, max_urls=5)
        assert len(urls) == 5


class TestIntelOrchestratorCleanup:
    @pytest.mark.asyncio
    async def test_close(self, orchestrator, mock_exa, mock_tavily, mock_firecrawl, mock_cache):
        await orchestrator.close()
        mock_exa.close.assert_called_once()
        mock_tavily.close.assert_called_once()
        mock_firecrawl.close.assert_called_once()
        mock_cache.close.assert_called_once()
