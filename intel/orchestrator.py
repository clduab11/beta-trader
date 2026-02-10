"""Intel Orchestrator — multi-source intelligence gathering with cost-optimized depth.

Implements the IntelOrchestrator from the ticket:
- SHALLOW: Exa only (5 results, ~$0.003, ~200ms)
- STANDARD: Exa + Tavily parallel (10 + 5 results, ~$0.035, ~300ms)
- DEEP: Exa → extract URLs → Firecrawl batch scrape (variable cost, ~2-5s)

Features:
- Depth-based source selection
- Result merging and deduplication
- Redis caching with TTL
- Cost tracking per query
- Event emission (IntelGathered)
"""

from __future__ import annotations

import asyncio
import re
import time
from typing import Literal

import structlog

from intel.cache import RedisCache
from intel.events import get_event_bus
from intel.sources.exa import COST_PER_RESULT as EXA_COST_PER_RESULT
from intel.sources.exa import ExaSource
from intel.sources.firecrawl import COST_PER_PAGE, FirecrawlSource
from intel.sources.tavily import COST_PER_SEARCH as TAVILY_COST_PER_SEARCH
from intel.sources.tavily import TavilySource
from intel.types import (
    IntelDepth,
    IntelQuery,
    IntelResult,
    IntelSource,
    SearchResult,
    Timestamp,
)

log = structlog.get_logger(__name__)

# URL extraction pattern for DEEP mode
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


class IntelOrchestrator:
    """Multi-source intelligence orchestrator with depth-based querying.

    Coordinates between Exa, Tavily, and Firecrawl sources based on
    the requested depth level, with Redis caching and cost tracking.
    """

    def __init__(
        self,
        exa: ExaSource | None = None,
        tavily: TavilySource | None = None,
        firecrawl: FirecrawlSource | None = None,
        cache: RedisCache | None = None,
        default_cache_ttl: int = 3600,
    ) -> None:
        self._exa = exa or ExaSource()
        self._tavily = tavily or TavilySource()
        self._firecrawl = firecrawl or FirecrawlSource()
        self._cache = cache
        self._default_cache_ttl = default_cache_ttl
        self._event_bus = get_event_bus()

    async def gather_intel(
        self,
        query: str | IntelQuery,
        depth: Literal["SHALLOW", "STANDARD", "DEEP"] | IntelDepth = IntelDepth.STANDARD,
    ) -> IntelResult:
        """Gather intelligence from multiple sources based on depth.

        Args:
            query: Either a string query or a full IntelQuery object.
            depth: Search depth (ignored if query is IntelQuery with depth set).

        Returns:
            IntelResult with merged, deduplicated results and cost tracking.
        """
        # Normalize input
        if isinstance(query, str):
            intel_query = IntelQuery(text=query, depth=IntelDepth(depth))
        else:
            intel_query = query

        start_time = time.monotonic()
        correlation_id = intel_query.correlation_id
        query_id_str = str(intel_query.query_id)

        log.info(
            "Intel query started",
            query_id=intel_query.query_id,
            depth=intel_query.depth,
            correlation_id=correlation_id,
        )

        # Emit query_started
        await self._event_bus.emit(
            event_type="query_started",
            payload={
                "query_id": query_id_str,
                "depth": intel_query.depth.value if hasattr(intel_query.depth, "value") else str(intel_query.depth),
                "correlation_id": correlation_id,
            },
            source_module="intel.orchestrator",
            correlation_id=correlation_id,
        )

        try:
            # Check cache
            if self._cache:
                cache_key = RedisCache.make_key(intel_query.text, intel_query.depth.value)
                cached = await self._cache.get(cache_key)
                if cached is not None:
                    cached.cached = True
                    latency_ms = (time.monotonic() - start_time) * 1000
                    cached.latency_ms = latency_ms

                    await self._emit_intel_gathered(cached, correlation_id)

                    # Emit query_completed for cache hit
                    await self._event_bus.emit(
                        event_type="query_completed",
                        payload={
                            "query_id": query_id_str,
                            "status": "success",
                            "cost": 0.0,
                            "latency": latency_ms,
                            "cached": True,
                        },
                        source_module="intel.orchestrator",
                        correlation_id=correlation_id,
                    )

                    log.info(
                        "Intel query served from cache",
                        query_id=intel_query.query_id,
                        latency_ms=round(latency_ms, 2),
                    )
                    return cached

            # Execute based on depth
            match intel_query.depth:
                case IntelDepth.SHALLOW:
                    result = await self._gather_shallow(intel_query)
                case IntelDepth.STANDARD:
                    result = await self._gather_standard(intel_query)
                case IntelDepth.DEEP:
                    result = await self._gather_deep(intel_query)

            # Finalize result
            result.latency_ms = (time.monotonic() - start_time) * 1000
            result.timestamp = Timestamp.now()

            # Store in cache
            if self._cache:
                ttl = intel_query.cache_ttl_seconds or self._default_cache_ttl
                cache_key = RedisCache.make_key(intel_query.text, intel_query.depth.value)
                await self._cache.set(cache_key, result, ttl=ttl)

            # Emit IntelGathered event
            await self._emit_intel_gathered(result, correlation_id)

            # Emit query_completed
            await self._event_bus.emit(
                event_type="query_completed",
                payload={
                    "query_id": query_id_str,
                    "status": "success",
                    "cost": result.total_cost_usd,
                    "latency": result.latency_ms,
                },
                source_module="intel.orchestrator",
                correlation_id=correlation_id,
            )

            log.info(
                "Intel query completed",
                query_id=intel_query.query_id,
                depth=result.depth_used,
                source_count=len(result.sources),
                total_cost_usd=round(result.total_cost_usd, 6),
                latency_ms=round(result.latency_ms, 2),
            )

            return result

        except Exception as e:
            # Emit error_occurred
            await self._event_bus.emit(
                event_type="error_occurred",
                payload={
                    "query_id": query_id_str,
                    "error_msg": str(e),
                    "source_module": "intel.orchestrator",
                },
                source_module="intel.orchestrator",
                correlation_id=correlation_id,
            )
            raise


    async def _gather_shallow(self, query: IntelQuery) -> IntelResult:
        """SHALLOW: Exa only, 5 results."""
        exa_results = await self._exa.search(
            query=query.text,
            num_results=5,
            correlation_id=query.correlation_id,
            query_id=str(query.query_id),
        )

        sources = self._convert_search_results(exa_results, "exa")
        cost = len(exa_results) * EXA_COST_PER_RESULT

        return IntelResult(
            query_id=query.query_id,
            correlation_id=query.correlation_id,
            sources=sources,
            merged_text=self._merge_snippets(sources),
            depth_used=IntelDepth.SHALLOW,
            total_cost_usd=cost,
        )

    async def _gather_standard(self, query: IntelQuery) -> IntelResult:
        """STANDARD: Exa + Tavily in parallel, skipping rate-limited sources."""
        exa_rate_limited = self._exa.is_rate_limited
        tavily_rate_limited = self._tavily.is_rate_limited

        tasks: list[asyncio.Task] = []
        task_labels: list[str] = []

        if not exa_rate_limited:
            exa_task = asyncio.ensure_future(
                self._exa.search(
                    query=query.text,
                    num_results=10,
                    correlation_id=query.correlation_id,
                    query_id=str(query.query_id),
                )
            )
            tasks.append(exa_task)
            task_labels.append("exa")
        else:
            log.info(
                "Exa source is rate-limited, skipping in STANDARD query",
                correlation_id=query.correlation_id,
            )

        if not tavily_rate_limited:
            tavily_task = asyncio.ensure_future(
                self._tavily.search(
                    query=query.text,
                    max_results=5,
                    correlation_id=query.correlation_id,
                    query_id=str(query.query_id),
                )
            )
            tasks.append(tavily_task)
            task_labels.append("tavily")
        else:
            log.info(
                "Tavily source is rate-limited, skipping in STANDARD query",
                correlation_id=query.correlation_id,
            )

        # Run available sources in parallel
        exa_results: list[SearchResult] = []
        tavily_results: list[SearchResult] = []

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for label, result in zip(task_labels, results, strict=True):
                if label == "exa":
                    if isinstance(result, list):
                        exa_results = result
                    else:
                        log.warning(
                            "Exa source failed in STANDARD query",
                            error=str(result),
                            correlation_id=query.correlation_id,
                        )
                elif label == "tavily":
                    if isinstance(result, list):
                        tavily_results = result
                    else:
                        log.warning(
                            "Tavily source failed in STANDARD query",
                            error=str(result),
                            correlation_id=query.correlation_id,
                        )

        # Merge and deduplicate
        sources = self._deduplicate_sources(
            self._convert_search_results(exa_results, "exa")
            + self._convert_search_results(tavily_results, "tavily")
        )

        # Calculate cost
        cost = len(exa_results) * EXA_COST_PER_RESULT
        if tavily_results:
            cost += TAVILY_COST_PER_SEARCH

        return IntelResult(
            query_id=query.query_id,
            correlation_id=query.correlation_id,
            sources=sources,
            merged_text=self._merge_snippets(sources),
            depth_used=IntelDepth.STANDARD,
            total_cost_usd=cost,
        )

    async def _gather_deep(self, query: IntelQuery) -> IntelResult:
        """DEEP: Exa → extract URLs → Firecrawl batch scrape."""
        # Step 1: Get initial results from Exa
        exa_results = await self._exa.search(
            query=query.text,
            num_results=10,
            correlation_id=query.correlation_id,
            query_id=str(query.query_id),
        )

        sources = self._convert_search_results(exa_results, "exa")
        cost = len(exa_results) * EXA_COST_PER_RESULT

        # Step 2: Extract URLs worth scraping
        urls_to_scrape = self._extract_scrape_urls(exa_results)

        if urls_to_scrape:
            # Step 3: Batch scrape with Firecrawl
            scraped = await self._firecrawl.batch_scrape(
                urls=urls_to_scrape,
                correlation_id=query.correlation_id,
                query_id=str(query.query_id),
            )

            # Add scraped content as additional sources
            for sc in scraped:

                sources.append(
                    IntelSource(
                        source_name="firecrawl",
                        url=sc.url,
                        title=sc.title,
                        snippet=sc.markdown[:500] if sc.markdown else sc.content[:500],
                        relevance_score=0.8,  # Scraped content is high-value
                        cost_usd=COST_PER_PAGE,
                        latency_ms=sc.latency_ms,
                    )
                )
                cost += COST_PER_PAGE

        sources = self._deduplicate_sources(sources)

        return IntelResult(
            query_id=query.query_id,
            correlation_id=query.correlation_id,
            sources=sources,
            merged_text=self._merge_snippets(sources),
            depth_used=IntelDepth.DEEP,
            total_cost_usd=cost,
        )

    @staticmethod
    def _convert_search_results(
        results: list[SearchResult], source_name: str
    ) -> list[IntelSource]:
        """Convert raw SearchResults into IntelSource objects.

        Per-result cost attribution:
        - Exa: ``EXA_COST_PER_RESULT`` per result (volume-based pricing).
        - Tavily: ``TAVILY_COST_PER_SEARCH / len(results)`` so the flat
          per-search fee is spread proportionally across results.
        """
        if source_name == "exa":
            per_result_cost = EXA_COST_PER_RESULT
        else:
            # Tavily charges per-search, not per-result.
            # Distribute the flat search cost across the returned results.
            per_result_cost = TAVILY_COST_PER_SEARCH / max(len(results), 1)

        return [
            IntelSource(
                source_name=source_name,
                url=r.url,
                title=r.title,
                snippet=r.snippet,
                relevance_score=r.relevance_score,
                cost_usd=per_result_cost,
            )
            for r in results
        ]

    @staticmethod
    def _deduplicate_sources(sources: list[IntelSource]) -> list[IntelSource]:
        """Deduplicate sources by URL, keeping the highest relevance score."""
        seen_urls: dict[str, IntelSource] = {}
        no_url_sources: list[IntelSource] = []

        for source in sources:
            if source.url:
                existing = seen_urls.get(source.url)
                if existing is None or source.relevance_score > existing.relevance_score:
                    seen_urls[source.url] = source
            else:
                no_url_sources.append(source)

        # Sort by relevance score descending
        deduped = list(seen_urls.values()) + no_url_sources
        deduped.sort(key=lambda s: s.relevance_score, reverse=True)
        return deduped

    @staticmethod
    def _merge_snippets(sources: list[IntelSource]) -> str:
        """Merge snippets from all sources into a single text summary."""
        # Deduplicate snippets by content similarity (simple approach)
        seen_snippets: set[str] = set()
        merged_parts: list[str] = []

        for source in sources:
            # Use first 100 chars as dedup key to catch near-duplicates
            dedup_key = source.snippet[:100].strip().lower()
            if dedup_key and dedup_key not in seen_snippets:
                seen_snippets.add(dedup_key)
                header = f"[{source.source_name}]"
                if source.title:
                    header += f" {source.title}"
                merged_parts.append(f"{header}\n{source.snippet}")

        return "\n\n".join(merged_parts)

    @staticmethod
    def _extract_scrape_urls(results: list[SearchResult], max_urls: int = 5) -> list[str]:
        """Extract high-value URLs from search results for deep scraping."""
        urls: list[str] = []
        for r in results:
            if r.url and len(urls) < max_urls:
                # Skip social media, search engines, etc.
                skip_patterns = [
                    "twitter.com",
                    "x.com",
                    "reddit.com",
                    "facebook.com",
                    "youtube.com",
                    "google.com",
                ]
                if not any(p in r.url.lower() for p in skip_patterns):
                    urls.append(r.url)
        return urls

    async def _emit_intel_gathered(
        self, result: IntelResult, correlation_id: str
    ) -> None:
        """Emit IntelGathered event per docs/interfaces/events.md."""
        await self._event_bus.emit(
            event_type="IntelGathered",
            payload={
                "query_id": result.query_id,
                "depth_used": result.depth_used.value,
                "source_count": len(result.sources),
                "total_cost_usd": round(result.total_cost_usd, 6),
                "latency_ms": round(result.latency_ms, 2),
                "cached": result.cached,
                "result_summary": result.merged_text[:200],
                "has_embeddings": result.embeddings is not None,
            },
            source_module="intel.orchestrator",
            correlation_id=correlation_id,
        )

    async def close(self) -> None:
        """Clean up all source clients and cache."""
        await self._exa.close()
        await self._tavily.close()
        await self._firecrawl.close()
        if self._cache:
            await self._cache.close()

    # Source accessors for status checking
    @property
    def exa(self) -> ExaSource:
        return self._exa

    @property
    def tavily(self) -> TavilySource:
        return self._tavily

    @property
    def firecrawl(self) -> FirecrawlSource:
        return self._firecrawl

    @property
    def cache(self) -> RedisCache | None:
        return self._cache
