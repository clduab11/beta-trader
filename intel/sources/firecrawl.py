"""Firecrawl deep web scraping source.

Provides full page content scraping and batch scraping via the Firecrawl API.
Includes circuit breaker, retry logic, concurrency limiting, and event emission.
Cost: variable per-page pricing (~$0.001/page).
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx
import structlog

from intel.circuit_breaker import INTEL_API_CONFIG, CircuitBreaker
from intel.errors import APIError, RateLimitError
from intel.events import get_event_bus
from intel.retry import retry_with_backoff
from intel.types import ScrapedContent

log = structlog.get_logger(__name__)

FIRECRAWL_API_BASE = "https://api.firecrawl.dev/v1"
COST_PER_PAGE = 0.001  # ~$0.001/page
MAX_CONCURRENT_SCRAPES = 5


class FirecrawlSource:
    """Firecrawl deep web scraping integration.

    Features:
    - Full page content scraping with markdown output
    - Batch processing with concurrency limit (5 concurrent)
    - Circuit breaker (3 failures in 60s → open for 60s)
    - Retry with exponential backoff (APIError: 3×1s/2s/4s; RateLimitError: 5×2s/4s/8s/16s/32s)
    - Rate limit tracking (429 → source marked rate-limited, short-circuits until window elapses)
    - Cost tracking (per-page pricing)
    - Event emission (SourceQueried, CircuitBreakerStateChanged)
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_concurrent: int = MAX_CONCURRENT_SCRAPES,
    ) -> None:
        self._api_key = api_key or os.environ.get("FIRECRAWL_API_KEY", "")
        self._timeout = timeout
        self._max_concurrent = max_concurrent
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker(
            service_name="firecrawl",
            config=INTEL_API_CONFIG,
            source_module="intel.firecrawl",
        )
        self._event_bus = get_event_bus()
        self._rate_limited_until: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily initialize the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=FIRECRAWL_API_BASE,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    def is_rate_limited(self) -> bool:
        """Return True if the source is currently rate-limited."""
        return time.monotonic() < self._rate_limited_until

    async def scrape(
        self,
        url: str,
        correlation_id: str = "",
        query_id: str | None = None,
    ) -> ScrapedContent:
        """Scrape a single URL for full page content.

        Args:
            url: URL to scrape.
            correlation_id: Tracing ID for the request chain.
            query_id: ID of the intel query.

        Returns:
            ScrapedContent with full page markdown/text.

        Raises:
            APIError: If the API returns a non-2xx response.
            RateLimitError: If the API returns HTTP 429.
            CircuitOpenError: If the circuit breaker is open.
        """
        start_time = time.monotonic()

        # Emit started event
        await self._event_bus.emit(
            event_type="source_querying",
            payload={
                "source_name": "firecrawl",
                "query_id": query_id,
                "status": "started",
                "url": url[:200],
            },
            source_module="intel.firecrawl",
            correlation_id=correlation_id,
        )

        try:
            result = await self._circuit_breaker.call(
                lambda: self._execute_scrape(url, correlation_id),
                query_id=query_id
            )

            latency_ms = (time.monotonic() - start_time) * 1000
            result.latency_ms = latency_ms
            result.cost_usd = COST_PER_PAGE

            # Emit completed event
            await self._event_bus.emit(
                event_type="SourceQueried",
                payload={
                    "source": "firecrawl",
                    "status": "completed",
                    "url": url[:200],
                    "latency_ms": round(latency_ms, 2),
                    "content_length": len(result.content),
                    "cost_usd": COST_PER_PAGE,
                },
                source_module="intel.firecrawl",
                correlation_id=correlation_id,
            )

            return result

        except Exception as exc:
            latency_ms = (time.monotonic() - start_time) * 1000

            # Mark source as rate-limited if applicable
            if isinstance(exc, RateLimitError):
                window = exc.retry_after_seconds if exc.retry_after_seconds else 60.0
                self._rate_limited_until = time.monotonic() + window

            # Emit failed event
            await self._event_bus.emit(
                event_type="SourceQueried",
                payload={
                    "source": "firecrawl",
                    "status": "failed",
                    "url": url[:200],
                    "latency_ms": round(latency_ms, 2),
                    "error": str(exc)[:200],
                },
                source_module="intel.firecrawl",
                correlation_id=correlation_id,
            )
            raise

    async def _execute_scrape(
        self,
        url: str,
        correlation_id: str,
    ) -> ScrapedContent:
        """Execute the actual scrape API call with retry logic."""

        async def _do_request() -> ScrapedContent:
            client = await self._get_client()
            start = time.monotonic()

            response = await client.post(
                "/scrape",
                json={
                    "url": url,
                    "formats": ["markdown", "rawHtml"],
                    "onlyMainContent": True,
                },
            )

            elapsed_ms = (time.monotonic() - start) * 1000

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", "2.0"))
                raise RateLimitError(
                    message="Firecrawl API rate limited",
                    source_module="intel.firecrawl",
                    service_name="firecrawl",
                    retry_after_seconds=retry_after,
                    correlation_id=correlation_id,
                )

            if response.status_code != 200:
                raise APIError(
                    message=f"Firecrawl API returned {response.status_code}: {response.text[:200]}",
                    source_module="intel.firecrawl",
                    service_name="firecrawl",
                    http_status=response.status_code,
                    endpoint="/scrape",
                    request_duration_ms=elapsed_ms,
                    correlation_id=correlation_id,
                )

            data = response.json()
            return self._parse_scrape_result(url, data)

        return await retry_with_backoff(
            _do_request,
            max_attempts=3,
            base_delay=1.0,
            max_delay=30.0,
            jitter=True,
            rate_limit_max_attempts=5,
            rate_limit_base_delay=2.0,
            rate_limit_max_delay=32.0,
        )

    @staticmethod
    def _parse_scrape_result(url: str, data: dict) -> ScrapedContent:
        """Parse Firecrawl scrape response into ScrapedContent."""
        page_data = data.get("data", data)
        return ScrapedContent(
            url=url,
            title=page_data.get("metadata", {}).get("title", ""),
            content=page_data.get("rawHtml", ""),
            markdown=page_data.get("markdown", ""),
            metadata=page_data.get("metadata", {}),
        )

    async def batch_scrape(
        self,
        urls: list[str],
        correlation_id: str = "",
        query_id: str | None = None,
    ) -> list[ScrapedContent]:
        """Scrape multiple URLs concurrently with a semaphore limit.

        Args:
            urls: List of URLs to scrape.
            correlation_id: Tracing ID for the request chain.
            query_id: ID of the intel query.

        Returns:
            List of ScrapedContent (failures are logged and skipped).
        """
        if not urls:
            return []

        log.info(
            "Starting batch scrape",
            url_count=len(urls),
            max_concurrent=self._max_concurrent,
            correlation_id=correlation_id,
        )

        async def _scrape_with_semaphore(url: str) -> ScrapedContent | None:
            async with self._semaphore:
                try:
                    return await self.scrape(url, correlation_id=correlation_id, query_id=query_id)
                except Exception:
                    log.warning(
                        "Batch scrape: single URL failed",
                        url=url[:200],
                        correlation_id=correlation_id,
                        exc_info=True,
                    )
                    return None

        tasks = [_scrape_with_semaphore(url) for url in urls]
        raw_results = await asyncio.gather(*tasks)

        results = [r for r in raw_results if r is not None]
        log.info(
            "Batch scrape completed",
            total_urls=len(urls),
            successful=len(results),
            failed=len(urls) - len(results),
            correlation_id=correlation_id,
        )
        return results

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Expose circuit breaker for status checks."""
        return self._circuit_breaker
