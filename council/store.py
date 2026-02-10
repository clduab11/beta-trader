"""Knowledge Store implementation using Redis Stack (JSON + Search)."""

from __future__ import annotations

import os
from typing import Any, List, Optional
from uuid import UUID

import structlog
from redis.asyncio import Redis
from redis.commands.search.field import TagField, TextField
from redis.commands.search.index_definition import IndexDefinition, IndexType
from redis.commands.search.query import Query
from redis.exceptions import ResponseError

from council.types import KnowledgeItem, KnowledgeSource

log = structlog.get_logger(__name__)

_DEFAULT_REDIS_URL = "redis://localhost:6379/1"  # Default to DB 1 for Knowledge
INDEX_NAME = "idx:knowledge"
PREFIX = "council:knowledge:"


class KnowledgeStore:
    """Async Redis Knowledge Store using Redis Stack (JSON + Search).
    
    Stores knowledge items as JSON documents and indexes them for full-text search.
    """

    def __init__(self, redis_url: str | None = None) -> None:
        self._redis_url = (
            redis_url
            or os.environ.get("REDIS_URL", _DEFAULT_REDIS_URL)
        )
        self._client: Redis | None = None

    async def connect(self) -> None:
        """Initialize Redis connection and ensure search index exists."""
        if self._client is None:
            self._client = Redis.from_url(self._redis_url, decode_responses=True)
            log.info("Knowledge Store connected", url=self._redis_url)
            await self._ensure_index()

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            log.info("Knowledge Store disconnected")

    async def _ensure_index(self) -> None:
        """Create the RediSearch index if it doesn't exist."""
        if not self._client:
            raise RuntimeError("Redis client not connected")

        schema = (
            TextField("$.content", as_name="content"),
            TagField("$.source", as_name="source"),
            TagField("$.tags[*]", as_name="tags"),
        )
        
        definition = IndexDefinition(
            prefix=[PREFIX],
            index_type=IndexType.JSON
        )

        try:
            await self._client.ft(INDEX_NAME).create_index(
                schema,
                definition=definition
            )
            log.info("Created Knowledge Store index", name=INDEX_NAME)
        except ResponseError as e:
            if "Index already exists" in str(e):
                log.debug("Knowledge Store index already exists")
            else:
                log.error("Failed to create index", error=str(e))
                raise

    async def add(self, item: KnowledgeItem) -> str:
        """Store a knowledge item.
        
        Args:
            item: The knowledge item to store.
            
        Returns:
            The key of the stored item.
        """
        if not self._client:
            await self.connect()

        key = f"{PREFIX}{item.id}"
        # Store as JSON
        await self._client.json().set(key, "$", item.model_dump(mode="json"))
        return key

    async def get(self, item_id: UUID | str) -> Optional[KnowledgeItem]:
        """Retrieve a knowledge item by ID.
        
        Args:
            item_id: UUID or string ID of the item.
            
        Returns:
            The KnowledgeItem if found, else None.
        """
        if not self._client:
            await self.connect()

        key = f"{PREFIX}{str(item_id)}"
        data = await self._client.json().get(key)
        
        if data:
            return KnowledgeItem.model_validate(data)
        return None

    async def search(
        self, 
        query_text: str, 
        limit: int = 10,
        source: Optional[KnowledgeSource] = None,
        tags: Optional[List[str]] = None
    ) -> List[KnowledgeItem]:
        """Search knowledge items.
        
        Args:
            query_text: Full text query string.
            limit: Max results to return.
            source: Filter by source.
            tags: Filter by tags (must match all if multiple).
            
        Returns:
            List of matching KnowledgeItems.
        """
        if not self._client:
            await self.connect()

        # Build query
        # Escape special characters in query text if needed, strictly simpler for now
        q_str = query_text
        
        if source:
            q_str += f" @source:{{{source.value}}}"
            
        if tags:
            for tag in tags:
                q_str += f" @tags:{{{tag}}}"

        query = Query(q_str).paging(0, limit)
        
        try:
            result = await self._client.ft(INDEX_NAME).search(query)
        except ResponseError as e:
            log.error("Search failed", query=q_str, error=str(e))
            return []

        items = []
        for doc in result.docs:
            try:
                # doc.json is a string representation of the JSON object
                data = doc.json
                # Depending on python-redis version, doc.json might be dict or string
                # If using decode_responses=True and JSON module, it usually returns string in search?
                # Actually RediSearch returns the fields. With JSON index, it returns `$` usually if loaded?
                # Wait, default behavior of search on JSON returns the root document string in `json` property
                
                if isinstance(data, str):
                    # It's a JSON string
                    parsed = KnowledgeItem.model_validate_json(data)
                    items.append(parsed)
                else:
                    log.warning("Unexpected doc format", doc=doc)
            except Exception as e:
                log.error("Failed to parse search result", doc_id=doc.id, error=str(e))
        
        return items

    async def delete(self, item_id: UUID | str) -> bool:
        """Delete a knowledge item.
        
        Returns:
            True if deleted, False if not found.
        """
        if not self._client:
            await self.connect()

        key = f"{PREFIX}{str(item_id)}"
        count = await self._client.json().delete(key)
        return count > 0
