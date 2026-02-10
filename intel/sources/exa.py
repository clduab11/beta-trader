"""Exa.ai neural search source.

Provides semantic/neural web search via the Exa API.
Includes circuit breaker, retry logic, and event emission.
Cost: ~$0.0025/query (5 results) or ~$0.005/query (10 results).
"""

from __future__ import annotations

import os
import time

import httpx
import structlog

from intel.circuit_breaker import INTEL_API_CONFIG, CircuitBreaker
from intel.errors import APIError, RateLimitError
from intel.events import get_event_bus
from intel.retry import retry_with_backoff
from intel.types import SearchResult

log = structlog.get_logger(__name__)

EXA_API_BASE = "https://api.exa.ai"
COST_PER_RESULT = 0.0005  # ~$0.0005 per result


class ExaSource:
    """Exa.ai neural search integration.

    Features:
    - Neural search API integration
    - Circuit breaker (3 failures in 60s → open for 60s)
    - Retry with exponential backoff (APIError: 3×1s/2s/4s; RateLimitError: 5×2s/4s/8s/16s/32s)
    - Rate limit tracking (429 → source marked rate-limited, short-circuits until window elapses)
    - Event emission (SourceQueried, CircuitBreakerStateChanged)
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("EXA_API_KEY", "")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker(
            service_name="exa",
            config=INTEL_API_CONFIG,
            source_module="intel.exa",
        )
        self._event_bus = get_event_bus()
        self._rate_limited_until: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily initialize the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=EXA_API_BASE,
                headers={
                    "x-api-key": self._api_key,
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

    async def search(
        self,
        query: str,
        num_results: int = 10,
        correlation_id: str = "",
        query_id: str | None = None,
    ) -> list[SearchResult]:
        """Search Exa.ai for semantically relevant results.

        Args:
            query: Natural language search query.
            num_results: Number of results to retrieve (default 10).
            correlation_id: Tracing ID for the request chain.
            query_id: ID of the intel query.

        Returns:
            List of SearchResult objects.

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
                "source_name": "exa",
                "query_id": query_id,
                "status": "started",
                "query": query[:100],
                "num_results": num_results,
            },
            source_module="intel.exa",
            correlation_id=correlation_id,
        )

        try:
            results = await self._circuit_breaker.call(
                lambda: self._execute_search(query, num_results, correlation_id),
                query_id=query_id
            )

            latency_ms = (time.monotonic() - start_time) * 1000

            # Emit completed event
            await self._event_bus.emit(
                event_type="SourceQueried",
                payload={
                    "source": "exa",
                    "status": "completed",
                    "latency_ms": round(latency_ms, 2),
                    "result_count": len(results),
                    "cost_usd": round(len(results) * COST_PER_RESULT, 6),
                },
                source_module="intel.exa",
                correlation_id=correlation_id,
            )

            return results


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
                    "source": "exa",
                    "status": "failed",
                    "latency_ms": round(latency_ms, 2),
                    "error": str(exc)[:200],
                },
                source_module="intel.exa",
                correlation_id=correlation_id,
            )
            raise

    async def _execute_search(
        self,
        query: str,
        num_results: int,
        correlation_id: str,
    ) -> list[SearchResult]:
        """Execute the actual API call with retry logic."""

        async def _do_request() -> list[SearchResult]:
            client = await self._get_client()
            start = time.monotonic()

            response = await client.post(
                "/search",
                json={
                    "query": query,
                    "numResults": num_results,
                    "useAutoprompt": True,
                    "type": "neural",
                    "contents": {
                        "text": {"maxCharacters": 1000},
                        "highlights": True,
                    },
                },
            )

            elapsed_ms = (time.monotonic() - start) * 1000

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", "2.0"))
                raise RateLimitError(
                    message="Exa API rate limited",
                    source_module="intel.exa",
                    service_name="exa",
                    retry_after_seconds=retry_after,
                    correlation_id=correlation_id,
                )

            if response.status_code != 200:
                raise APIError(
                    message=f"Exa API returned {response.status_code}: {response.text[:200]}",
                    source_module="intel.exa",
                    service_name="exa",
                    http_status=response.status_code,
                    endpoint="/search",
                    request_duration_ms=elapsed_ms,
                    correlation_id=correlation_id,
                )

            data = response.json()
            return self._parse_results(data)

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
    def _parse_results(data: dict) -> list[SearchResult]:
        """Parse Exa API response into SearchResult objects."""
        results: list[SearchResult] = []
        for item in data.get("results", []):
            # Extract text content
            text = ""
            if "text" in item:
                text = item["text"]
            elif "highlights" in item and item["highlights"]:
                text = " ".join(item["highlights"])

            results.append(
                SearchResult(
                    url=item.get("url"),
                    title=item.get("title", ""),
                    snippet=text[:500] if text else item.get("title", ""),
                    relevance_score=item.get("score", 0.0),
                    source_name="exa",
                    raw_data=item,
                )
            )
        return results

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Expose circuit breaker for status checks."""
        return self._circuit_breaker
