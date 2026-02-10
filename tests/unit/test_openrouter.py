import pytest
import os
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock, ANY
from routing.openrouter.client import OpenRouterClient, CompletionResult, LLMResponse
from routing.openrouter.models import ModelRotator
from intel.errors import RateLimitError, APIError, ConfigurationError

# Unit tests for ModelRotator

def test_model_rotator_initialization():
    rotator = ModelRotator()
    assert len(rotator.models) > 0
    assert rotator.current_index == 0
    assert len(rotator.rate_limited) == 0

def test_get_next_model_rotation():
    rotator = ModelRotator()
    # Mock models for predictability
    rotator.models = [
        {"id": "m1", "strength": "reasoning", "context": 100, "name": "M1", "notes": ""},
        {"id": "m2", "strength": "reasoning", "context": 100, "name": "M2", "notes": ""}
    ]
    
    m1 = rotator.get_next_model("reasoning")
    m2 = rotator.get_next_model("reasoning")
    m3 = rotator.get_next_model("reasoning")
    
    assert m1 == "m1"
    assert m2 == "m2"
    assert m3 == "m1" # Rotated back

def test_get_next_model_task_preference():
    rotator = ModelRotator()
    rotator.models = [
        {"id": "reason", "strength": "reasoning", "context": 100, "name": "R", "notes": ""},
        {"id": "code", "strength": "coding", "context": 100, "name": "C", "notes": ""}
    ]
    
    assert rotator.get_next_model("coding") == "code"
    assert rotator.get_next_model("reasoning") == "reason"

def test_mark_rate_limited():
    rotator = ModelRotator()
    rotator.models = [
        {"id": "m1", "strength": "general", "context": 100, "name": "M1", "notes": ""},
        {"id": "m2", "strength": "general", "context": 100, "name": "M2", "notes": ""}
    ]
    
    m1 = rotator.get_next_model("general")
    assert m1 == "m1"
    
    rotator.mark_rate_limited("m1")
    assert "m1" in rotator.rate_limited
    
    # Should skip m1
    m2 = rotator.get_next_model("general")
    assert m2 == "m2"

def test_reset_when_all_rate_limited():
    rotator = ModelRotator()
    rotator.models = [{"id": "m1", "strength": "general", "context": 100, "name": "M1", "notes": ""}]
    
    rotator.mark_rate_limited("m1")
    
    # Next call should clear rate_limited and return m1
    with patch('time.sleep'): # Avoid waiting
        m = rotator.get_next_model("general")
    assert m == "m1"
    assert len(rotator.rate_limited) == 0

# Test Client

@pytest.mark.asyncio
async def test_client_missing_api_key():
    with patch.dict("os.environ", {}, clear=True):
        client = OpenRouterClient(api_key=None)
        with pytest.raises(ConfigurationError):
             await client.complete("test")

@pytest.mark.asyncio
async def test_complete_success():
    client = OpenRouterClient(api_key="test-key")
    
    mock_result = CompletionResult(
        content="Success", 
        model="m1", 
        usage={"total_tokens": 10}, 
        metadata={}
    )
    
    with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_make:
        mock_make.return_value = mock_result
        
        response = await client.complete("test")
        
        assert isinstance(response, CompletionResult)
        assert response.content == "Success"
        assert response.model == "m1"

@pytest.mark.asyncio
async def test_backoff_logic():
    client = OpenRouterClient(api_key="test-key")
    
    # Let's patch _make_request
    with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_req:
        mock_req.side_effect = [
            APIError("Fail 1", source_module="test"),
            APIError("Fail 2", source_module="test"),
            CompletionResult(content="Success", model="m1", usage={})
        ]
        
        # We also want to ensure sleep is called with correct delays
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
             response = await client.complete("test")
             
             assert response.content == "Success"
             assert mock_req.call_count == 3
             # delays: 0.5, 1.0 (before 3rd attempt)
             assert mock_sleep.call_count == 2
             mock_sleep.assert_any_call(0.5)
             mock_sleep.assert_any_call(1.0)

@pytest.mark.asyncio
async def test_circuit_breaker_and_rotation_on_429():
    client = OpenRouterClient(api_key="test-key")
    client.rotator.models = [
        {"id": "m1", "strength": "general", "context": 100, "name": "M1", "notes": ""},
        {"id": "m2", "strength": "general", "context": 100, "name": "M2", "notes": ""}
    ]
    
    mock_success = CompletionResult(content="Success", model="m2", usage={})
    
    with patch.object(client, '_make_request', new_callable=AsyncMock) as mock_req:
        async def side_effect(prompt, model_id, max_tokens):
            if model_id == "m1":
                raise RateLimitError("Limit", source_module="test", retry_after_seconds=1)
            return mock_success
        
        mock_req.side_effect = side_effect
        
        # Patch event bus to capture events
        with patch.object(client.event_bus, 'emit', new_callable=AsyncMock) as mock_emit:
            response = await client.complete("test")
            
            assert response.content == "Success"
            assert response.model == "m2"
            
            # Check if m1 was marked rate limited
            assert "m1" in client.rotator.rate_limited
            
            # Check events
            calls = [c[0][0] for c in mock_emit.call_args_list]
            assert "RateLimitHit" in calls
            assert "ModelRotated" in calls
            assert "CompletionGenerated" in calls
