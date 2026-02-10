"""Unit tests for JinaEmbedder client."""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import httpx
import pytest

from council.embedder import EMBEDDING_DIM, JinaEmbedder
from intel.errors import APIError, RateLimitError


@pytest.fixture
def embedder():
    return JinaEmbedder(api_key="test-key")


class TestJinaEmbedder:

    @pytest.mark.asyncio
    async def test_embed_success(self, embedder):
        fake_vector = [0.01] * EMBEDDING_DIM
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": fake_vector}]
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        embedder._client = mock_client

        result = await embedder.embed("test text")
        assert len(result) == EMBEDDING_DIM
        assert result == fake_vector

        mock_client.post.assert_called_once()
        call_kwargs = mock_client.post.call_args
        assert call_kwargs[0][0] == "/embeddings"

    @pytest.mark.asyncio
    async def test_embed_rate_limit(self, embedder):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "5.0"}
        mock_response.text = "Rate limited"

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        embedder._client = mock_client

        with pytest.raises(RateLimitError, match="Jina API rate limited"):
            await embedder.embed("test text")

        assert embedder.is_rate_limited

    @pytest.mark.asyncio
    async def test_embed_api_error(self, embedder):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_response.headers = {}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        embedder._client = mock_client

        with pytest.raises(APIError, match="Jina API returned 500"):
            await embedder.embed("test text")

    @pytest.mark.asyncio
    async def test_embed_empty_response_raises(self, embedder):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": []}

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        embedder._client = mock_client

        with pytest.raises(ValueError, match="no embeddings"):
            await embedder.embed("test text")

    @pytest.mark.asyncio
    async def test_embed_wrong_dim_raises(self, embedder):
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1] * 100}]
        }

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.post.return_value = mock_response
        mock_client.is_closed = False
        embedder._client = mock_client

        with pytest.raises(ValueError, match="768-dim"):
            await embedder.embed("test text")

    @pytest.mark.asyncio
    async def test_close(self, embedder):
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.is_closed = False
        embedder._client = mock_client

        await embedder.close()
        mock_client.aclose.assert_called_once()
        assert embedder._client is None

    def test_circuit_breaker_exposed(self, embedder):
        cb = embedder.circuit_breaker
        assert cb.service_name == "jina"
