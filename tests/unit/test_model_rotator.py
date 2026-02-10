import pytest
import time
from unittest.mock import Mock
from routing.openrouter.models import ModelRotator

def test_reset_when_all_rate_limited_with_wait():
    """Test that rotator waits 60s when all models are rate limited."""
    mock_wait = Mock()
    rotator = ModelRotator(wait_handler=mock_wait)
    rotator.models = [{"id": "m1", "strength": "general", "context": 100, "name": "M1", "notes": ""}]
    
    # Mark the only model as rate limited
    rotator.mark_rate_limited("m1")
    
    # Next call should trigger wait, clear rate_limited, and return m1
    m = rotator.get_next_model("general")
    
    assert m == "m1"
    assert len(rotator.rate_limited) == 0
    mock_wait.assert_called_once_with(60.0)
