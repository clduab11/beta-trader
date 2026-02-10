"""Jina AI embedder client with retry and circuit-breaker support.

Produces 768-dimensional embeddings via Jina Embeddings v2 API.
Follows the same resilience patterns as intel sources (ExaSource, etc.).
"""

from __future__ import annotations

import os
import time

import httpx
import structlog

from intel.circuit_breaker import CircuitBreaker, CircuitBreakerConfig
from intel.errors import APIError, RateLimitError
from intel.retry import retry_with_backoff

log = structlog.get_logger(__name__)

JINA_API_BASE = "https://api.jina.ai/v1"
EMBEDDING_MODEL = "jina-embeddings-v2-base-en"
EMBEDDING_DIM = 768

# Circuit breaker config — same cadence as other intel APIs
JINA_CB_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    timeout_seconds=60.0,
    half_open_max_calls=1,
    failure_window_seconds=60.0,
)


class JinaEmbedder:
    """Async Jina Embeddings client with circuit-breaker and retry.

    Usage::

        embedder = JinaEmbedder()
        vector = await embedder.embed("some text to embed")
        await embedder.close()
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key or os.environ.get("JINA_API_KEY", "")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._circuit_breaker = CircuitBreaker(
            service_name="jina",
            config=JINA_CB_CONFIG,
            source_module="council.embedder",
        )
        self._rate_limited_until: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=JINA_API_BASE,
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
        return time.monotonic() < self._rate_limited_until

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._circuit_breaker

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string, returning a 768-dim float vector.

        Raises:
            APIError: On non-2xx Jina response.
            RateLimitError: On HTTP 429.
            CircuitOpenError: If the circuit breaker is open.
            ValueError: If the response does not contain a valid embedding.
        """
        return await self._circuit_breaker.call(
            lambda: self._execute_embed(text)
        )

    async def _execute_embed(self, text: str) -> list[float]:
        """Execute the Jina embedding request with retry."""

        async def _do_request() -> list[float]:
            client = await self._get_client()
            start = time.monotonic()

            response = await client.post(
                "/embeddings",
                json={
                    "model": EMBEDDING_MODEL,
                    "input": [text],
                },
            )

            elapsed_ms = (time.monotonic() - start) * 1000

            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", "2.0"))
                self._rate_limited_until = time.monotonic() + retry_after
                raise RateLimitError(
                    message="Jina API rate limited",
                    source_module="council.embedder",
                    service_name="jina",
                    retry_after_seconds=retry_after,
                )

            if response.status_code != 200:
                raise APIError(
                    message=f"Jina API returned {response.status_code}: {response.text[:200]}",
                    source_module="council.embedder",
                    service_name="jina",
                    http_status=response.status_code,
                    endpoint="/embeddings",
                    request_duration_ms=elapsed_ms,
                )

            data = response.json()
            embeddings = data.get("data", [])
            if not embeddings:
                raise ValueError("Jina response contained no embeddings")

            vector: list[float] = embeddings[0].get("embedding", [])
            if len(vector) != EMBEDDING_DIM:
                raise ValueError(
                    f"Expected {EMBEDDING_DIM}-dim vector, got {len(vector)}"
                )

            return vector

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
