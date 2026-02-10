"""Unit tests for source clients (Exa, Tavily, Firecrawl) with mocked HTTP."""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from intel.errors import APIError, RateLimitError
from intel.events import reset_event_bus
from intel.sources.exa import ExaSource
from intel.sources.firecrawl import FirecrawlSource
from intel.sources.tavily import TavilySource


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


def _mock_response(status_code: int = 200, json_data: dict | None = None, text: str = ""):
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.text = text or json.dumps(json_data or {})
    resp.headers = {}
    resp.json.return_value = json_data or {}
    return resp


# ─── Exa Source Tests ───────────────────────────────────────────────────────────


class TestExaSource:
    @pytest.fixture
    def exa(self):
        source = ExaSource(api_key="test-key")
        return source

    @pytest.mark.asyncio
    async def test_search_success(self, exa):
        mock_response = _mock_response(
            200,
            {
                "results": [
                    {
                        "url": "https://example.com/1",
                        "title": "Result 1",
                        "text": "Content about BTC ETF approval",
                        "score": 0.95,
                    },
                    {
                        "url": "https://example.com/2",
                        "title": "Result 2",
                        "text": "More info about crypto",
                        "score": 0.88,
                    },
                ]
            },
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        exa._client = mock_client

        results = await exa.search("BTC ETF approval", num_results=5)

        assert len(results) == 2
        assert results[0].source_name == "exa"
        assert results[0].title == "Result 1"
        assert results[0].relevance_score == 0.95
        assert results[0].url == "https://example.com/1"

    @pytest.mark.asyncio
    async def test_search_rate_limit(self, exa):
        mock_response = _mock_response(429)
        mock_response.headers = {"Retry-After": "5"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        exa._client = mock_client

        with pytest.raises(RateLimitError):
            await exa.search("test query")

    @pytest.mark.asyncio
    async def test_search_api_error(self, exa):
        mock_response = _mock_response(500, text="Internal Server Error")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        exa._client = mock_client

        with pytest.raises(APIError):
            await exa.search("test query")

    @pytest.mark.asyncio
    async def test_parse_results_with_highlights(self):
        data = {
            "results": [
                {
                    "url": "https://example.com",
                    "title": "Test",
                    "highlights": ["Important fact 1", "Important fact 2"],
                    "score": 0.9,
                }
            ]
        }
        results = ExaSource._parse_results(data)
        assert len(results) == 1
        assert "Important fact 1" in results[0].snippet

    @pytest.mark.asyncio
    async def test_parse_results_empty(self):
        results = ExaSource._parse_results({"results": []})
        assert results == []


# ─── Tavily Source Tests ────────────────────────────────────────────────────────


class TestTavilySource:
    @pytest.fixture
    def tavily(self):
        return TavilySource(api_key="test-key")

    @pytest.mark.asyncio
    async def test_search_success(self, tavily):
        mock_response = _mock_response(
            200,
            {
                "results": [
                    {
                        "url": "https://news.com/1",
                        "title": "Breaking News",
                        "content": "Latest crypto market update...",
                        "score": 0.92,
                    }
                ]
            },
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        tavily._client = mock_client

        results = await tavily.search("crypto news", max_results=5)

        assert len(results) == 1
        assert results[0].source_name == "tavily"
        assert results[0].title == "Breaking News"

    @pytest.mark.asyncio
    async def test_search_rate_limit(self, tavily):
        mock_response = _mock_response(429)
        mock_response.headers = {"Retry-After": "2"}

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        tavily._client = mock_client

        with pytest.raises(RateLimitError):
            await tavily.search("test query")


# ─── Firecrawl Source Tests ─────────────────────────────────────────────────────


class TestFirecrawlSource:
    @pytest.fixture
    def firecrawl(self):
        return FirecrawlSource(api_key="test-key")

    @pytest.mark.asyncio
    async def test_scrape_success(self, firecrawl):
        mock_response = _mock_response(
            200,
            {
                "data": {
                    "markdown": "# Page Title\n\nPage content here",
                    "rawHtml": "<html><body>Page content here</body></html>",
                    "metadata": {
                        "title": "Page Title",
                        "sourceURL": "https://example.com/page",
                    },
                }
            },
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        firecrawl._client = mock_client

        result = await firecrawl.scrape("https://example.com/page")

        assert result.url == "https://example.com/page"
        assert result.title == "Page Title"
        assert "Page content" in result.markdown

    @pytest.mark.asyncio
    async def test_batch_scrape_success(self, firecrawl):
        mock_response = _mock_response(
            200,
            {
                "data": {
                    "markdown": "# Content",
                    "rawHtml": "<html>Content</html>",
                    "metadata": {"title": "Test"},
                }
            },
        )

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        firecrawl._client = mock_client

        urls = ["https://example.com/1", "https://example.com/2"]
        results = await firecrawl.batch_scrape(urls)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_batch_scrape_partial_failure(self, firecrawl):
        """Batch scrape continues when individual URLs fail."""

        async def _mock_post(url, **kwargs):
            body = kwargs.get("json", {})
            target_url = body.get("url", "")
            if "fail.com" in target_url:
                return _mock_response(500, text="Error")
            return _mock_response(
                200,
                {
                    "data": {
                        "markdown": "# OK",
                        "rawHtml": "<html>OK</html>",
                        "metadata": {"title": "OK"},
                    }
                },
            )

        mock_client = AsyncMock()
        mock_client.post = _mock_post
        mock_client.is_closed = False
        firecrawl._client = mock_client

        urls = ["https://fail.com", "https://ok.com"]
        results = await firecrawl.batch_scrape(urls)

        # Only the successful one should be returned
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_batch_scrape_empty(self, firecrawl):
        results = await firecrawl.batch_scrape([])
        assert results == []

    @pytest.mark.asyncio
    async def test_scrape_api_error(self, firecrawl):
        mock_response = _mock_response(500, text="Internal Error")

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        firecrawl._client = mock_client

        with pytest.raises(APIError):
            await firecrawl.scrape("https://example.com")
