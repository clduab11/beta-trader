"""Unit tests for Knowledge Store."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from redis.exceptions import ResponseError

from council.store import KnowledgeStore
from council.types import KnowledgeItem, KnowledgeSource

@pytest.fixture
def mock_redis():
    mock = AsyncMock()
    # Mock FT object returns
    ft_mock = AsyncMock()
    ft_mock.create_index = AsyncMock()
    ft_mock.search = AsyncMock()
    mock.ft = MagicMock(return_value=ft_mock)  # Not AsyncMock, it's a factory method on client
    
    # Mock JSON object returns
    json_mock = AsyncMock()
    json_mock.set = AsyncMock()
    json_mock.get = AsyncMock()
    json_mock.delete = AsyncMock()
    mock.json = MagicMock(return_value=json_mock)
    
    return mock

@pytest.fixture
def store(mock_redis):
    s = KnowledgeStore()
    # Don't set _client here; tests that need it will set it themselves.
    # For connect() tests, we patch Redis.from_url instead.
    s._client = mock_redis
    return s


@pytest.fixture
def fresh_store():
    """A store without a pre-set client, for testing connect()."""
    return KnowledgeStore(redis_url="redis://localhost:6379/1")

class TestKnowledgeStore:

    @pytest.mark.asyncio
    async def test_connect_creates_index(self, fresh_store, mock_redis):
        with patch("council.store.Redis.from_url", return_value=mock_redis):
            await fresh_store.connect()
        mock_redis.ft.assert_called_with("idx:knowledge")
        mock_redis.ft.return_value.create_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_handles_existing_index(self, fresh_store, mock_redis):
        mock_redis.ft.return_value.create_index.side_effect = ResponseError("Index already exists")
        with patch("council.store.Redis.from_url", return_value=mock_redis):
            await fresh_store.connect()  # Should not raise
        mock_redis.ft.return_value.create_index.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_add_item(self, store, mock_redis):
        item = KnowledgeItem(content="test info", source=KnowledgeSource.USER)
        key = await store.add(item)
        
        assert key.startswith("council:knowledge:")
        mock_redis.json.return_value.set.assert_called_once()
        
        # Verify args
        call_args = mock_redis.json.return_value.set.call_args
        assert call_args[0][0] == key
        assert call_args[0][1] == "$"
        assert call_args[0][2]["content"] == "test info"

    @pytest.mark.asyncio
    async def test_get_item(self, store, mock_redis):
        item = KnowledgeItem(content="retrieved", source=KnowledgeSource.INTEL)
        mock_redis.json.return_value.get.return_value = item.model_dump(mode="json")
        
        retrieved = await store.get(item.id)
        assert retrieved is not None
        assert retrieved.id == item.id
        assert retrieved.content == "retrieved"

    @pytest.mark.asyncio
    async def test_get_item_none(self, store, mock_redis):
        mock_redis.json.return_value.get.return_value = None
        retrieved = await store.get(uuid4())
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_search_parse(self, store, mock_redis):
        # Setup search result
        mock_doc = MagicMock()
        item = KnowledgeItem(content="found me", source=KnowledgeSource.SYSTEM)
        mock_doc.json = item.model_dump_json()
        mock_doc.id = f"council:knowledge:{item.id}"
        
        mock_result = MagicMock()
        mock_result.docs = [mock_doc]
        
        mock_redis.ft.return_value.search.return_value = mock_result
        
        results = await store.search("found")
        assert len(results) == 1
        assert results[0].content == "found me"
        assert results[0].id == item.id

    @pytest.mark.asyncio
    async def test_delete(self, store, mock_redis):
        mock_redis.json.return_value.delete.return_value = 1
        result = await store.delete(uuid4())
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found(self, store, mock_redis):
        mock_redis.json.return_value.delete.return_value = 0
        result = await store.delete(uuid4())
        assert result is False
