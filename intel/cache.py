"""Redis cache wrapper for Intel pipeline results.

Uses Redis db0 with TTL-based expiration.
Key format: intel:cache:{sha256(query + depth)}
Serialization: JSON via Pydantic.
"""

from __future__ import annotations

import hashlib
import json
import os

import structlog
from redis.asyncio import Redis

from intel.types import IntelResult

log = structlog.get_logger(__name__)

DEFAULT_TTL = 3600  # 1 hour
_DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class RedisCache:
    """Async Redis cache for IntelResult objects.

    Uses db0 for cache storage with TTL-based expiration.
    Reads ``REDIS_URL`` from the environment when no explicit URL is provided.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = (
            redis_url
            or os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
        )
        # Ensure db0 suffix for cache isolation
        if not self._redis_url.endswith("/0"):
            self._redis_url = self._redis_url.rstrip("/") + "/0"
        self._client: Redis | None = None

    async def connect(self) -> None:
        """Initialize Redis connection."""
        if self._client is None:
            self._client = Redis.from_url(self._redis_url, decode_responses=True)
            log.info("Redis cache connected", url=self._redis_url)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            log.info("Redis cache disconnected")

    @property
    def client(self) -> Redis:
        """Get the Redis client, raising if not connected."""
        if self._client is None:
            raise RuntimeError("RedisCache not connected. Call connect() first.")
        return self._client

    @staticmethod
    def make_key(query: str, depth: str) -> str:
        """Generate a cache key from query text and depth.

        Key format: intel:cache:{sha256(query + depth)}
        """
        hash_input = f"{query}:{depth}"
        digest = hashlib.sha256(hash_input.encode()).hexdigest()
        return f"intel:cache:{digest}"

    async def get(self, key: str) -> IntelResult | None:
        """Retrieve a cached IntelResult by key.

        Returns None on cache miss or deserialization errors.
        """
        try:
            raw = await self.client.get(key)
            if raw is None:
                log.debug("Cache miss", key=key)
                return None

            data = json.loads(raw)
            result = IntelResult.model_validate(data)
            result.cached = True
            log.debug("Cache hit", key=key, query_id=result.query_id)
            return result
        except Exception:
            log.warning("Cache get failed", key=key, exc_info=True)
            return None

    async def set(self, key: str, value: IntelResult, ttl: int = DEFAULT_TTL) -> None:
        """Store an IntelResult in the cache with TTL.

        Args:
            key: Cache key.
            value: IntelResult to cache.
            ttl: Time-to-live in seconds (default 1 hour).
        """
        try:
            serialized = value.model_dump_json()
            await self.client.set(key, serialized, ex=ttl)
            log.debug("Cache set", key=key, ttl=ttl, query_id=value.query_id)
        except Exception:
            log.warning("Cache set failed", key=key, exc_info=True)

    async def delete(self, key: str) -> bool:
        """Delete a cache entry. Returns True if the key existed."""
        try:
            result = await self.client.delete(key)
            return bool(result)
        except Exception:
            log.warning("Cache delete failed", key=key, exc_info=True)
            return False

    async def clear_all(self) -> None:
        """Clear all intel cache keys (keys matching intel:cache:*)."""
        try:
            cursor = "0"
            while True:
                cursor, keys = await self.client.scan(
                    cursor=cursor, match="intel:cache:*", count=100
                )
                if keys:
                    await self.client.delete(*keys)
                if cursor == "0" or cursor == 0:
                    break
            log.info("Cache cleared")
        except Exception:
            log.warning("Cache clear failed", exc_info=True)

    async def health_check(self) -> bool:
        """Check if Redis is reachable."""
        try:
            await self.client.ping()
            return True
        except Exception:
            return False
