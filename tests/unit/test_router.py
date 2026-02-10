import pytest
from unittest.mock import AsyncMock, Mock
from routing.router import ThreeTierRouter
from routing.openrouter.client import CompletionResult, LLMUsage

@pytest.mark.asyncio
async def test_route_tier3_heuristics():
    # Mock client
    mock_client = Mock()
    mock_client.complete = AsyncMock(return_value=CompletionResult(
        content="Success", model="model", usage=LLMUsage()
    ))
    
    router = ThreeTierRouter(client=mock_client)
    
    # Text length > 500
    long_prompt = "a" * 501
    await router.route(long_prompt)
    mock_client.complete.assert_called_with(long_prompt, task_type="reasoning")
    
    # Keyword check
    await router.route("Please explain this")
    mock_client.complete.assert_called_with("Please explain this", task_type="reasoning")
    
    # Complexity override
    await router.route("short", complexity="high")
    mock_client.complete.assert_called_with("short", task_type="reasoning")

@pytest.mark.asyncio
async def test_route_tier2_heuristics():
    mock_client = Mock()
    mock_client.complete = AsyncMock(return_value=CompletionResult(
        content="Success", model="model", usage=LLMUsage()
    ))
    
    router = ThreeTierRouter(client=mock_client)
    
    # Simple short prompt
    short_prompt = "Hello world"
    await router.route(short_prompt)
    mock_client.complete.assert_called_with(short_prompt, task_type="general")
