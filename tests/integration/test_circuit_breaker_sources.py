"""Circuit breaker integration tests with source clients.

Validates:
- Circuit breaker opens after failure threshold
- Circuit breaker blocks requests when open
- Circuit breaker transitions to HALF_OPEN after timeout
- Circuit breaker closes on successful probe
- CircuitBreakerStateChanged events are emitted
"""

import asyncio
import contextlib
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from intel.circuit_breaker import CircuitBreakerConfig, CircuitState
from intel.errors import CircuitOpenError
from intel.events import get_event_bus, reset_event_bus
from intel.sources.exa import ExaSource
from intel.sources.tavily import TavilySource


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


@pytest.fixture(autouse=True)
def _fast_sleep():
    """Patch asyncio.sleep to avoid real delays during retry backoff.

    Preserves short sleeps (<0.01s) to allow event loop yields.
    """
    _original_sleep = asyncio.sleep

    async def _patched_sleep(delay, *args, **kwargs):
        if delay <= 0.01:
            # Allow event loop yields for fire-and-forget tasks
            await _original_sleep(0)
        # Skip long retry backoff sleeps

    with patch("asyncio.sleep", side_effect=_patched_sleep):
        yield


def _error_http_client(status_code: int = 500):
    """Mock client that always returns an error."""
    client = AsyncMock()
    client.is_closed = False

    async def _post(url, **kwargs):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = status_code
        resp.json.return_value = {}
        resp.text = "Server Error"
        resp.headers = {}
        return resp

    client.post = _post
    return client


def _success_http_client(response_json: dict):
    """Mock client that returns success."""
    client = AsyncMock()
    client.is_closed = False

    async def _post(url, **kwargs):
        resp = MagicMock(spec=httpx.Response)
        resp.status_code = 200
        resp.json.return_value = response_json
        resp.text = json.dumps(response_json)
        resp.headers = {}
        return resp

    client.post = _post
    return client


class TestExaCircuitBreaker:
    """Test circuit breaker behavior within ExaSource."""

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        exa = ExaSource(api_key="test")
        # Override circuit breaker with a low threshold for testing
        exa._circuit_breaker.config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_seconds=60.0,
            half_open_max_calls=1,
            failure_window_seconds=60.0,
        )
        exa._client = _error_http_client(500)

        # Cause 3 failures (retry mechanism will try 3 times per search call)
        for _ in range(3):
            with contextlib.suppress(Exception):
                await exa.search("test")

        # Circuit should now be open
        assert exa.circuit_breaker.state == CircuitState.OPEN

        # Next call should raise CircuitOpenError
        with pytest.raises(CircuitOpenError):
            await exa.search("test")

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_changed_event(self):
        events: list[dict] = []

        async def capture(event: dict):
            events.append(event)

        bus = get_event_bus()
        bus.subscribe("CircuitBreakerStateChanged", capture)

        exa = ExaSource(api_key="test")
        exa._circuit_breaker.config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_seconds=60.0,
            half_open_max_calls=1,
            failure_window_seconds=60.0,
        )
        exa._client = _error_http_client(500)

        # Trigger failures to open circuit
        for _ in range(3):
            with contextlib.suppress(Exception):
                await exa.search("test")

        # Allow event loop to process the fire-and-forget event task
        await asyncio.sleep(0.001)

        # Should have CircuitBreakerStateChanged event for OPEN transition
        cb_events = [e for e in events if e["event_type"] == "CircuitBreakerStateChanged"]
        assert len(cb_events) >= 1
        open_event = next((e for e in cb_events if e["payload"]["state"] == "OPEN"), None)
        assert open_event is not None
        assert open_event["payload"]["source"] == "exa"

    @pytest.mark.asyncio
    async def test_circuit_closes_after_successful_probe(self):
        exa = ExaSource(api_key="test")
        exa._circuit_breaker.config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_seconds=0.1,  # Very short timeout for testing
            half_open_max_calls=1,
            failure_window_seconds=60.0,
        )
        exa._client = _error_http_client(500)

        # Open the circuit
        for _ in range(3):
                with contextlib.suppress(Exception):
                    await exa.search("test")
        assert exa.circuit_breaker.state == CircuitState.OPEN

        # Simulate timeout expiry by backdating opened_at
        exa._circuit_breaker._opened_at = time.monotonic() - 1.0

        # Replace with success client
        exa._client = _success_http_client({
            "results": [{"url": "https://ex.com/1", "title": "T", "text": "C", "score": 0.9}]
        })

        # Successful probe should close circuit
        result = await exa.search("test")
        assert len(result) == 1
        assert exa.circuit_breaker.state == CircuitState.CLOSED


class TestTavilyCircuitBreaker:
    """Test circuit breaker for TavilySource."""

    @pytest.mark.asyncio
    async def test_tavily_circuit_opens(self):
        tavily = TavilySource(api_key="test")
        tavily._circuit_breaker.config = CircuitBreakerConfig(
            failure_threshold=3,
            timeout_seconds=60.0,
            half_open_max_calls=1,
            failure_window_seconds=60.0,
        )
        tavily._client = _error_http_client(500)

        for _ in range(3):
                with contextlib.suppress(Exception):
                    await tavily.search("test")
        assert tavily.circuit_breaker.state == CircuitState.OPEN

        with pytest.raises(CircuitOpenError):
            await tavily.search("test")


class TestCircuitBreakerGracefulDegradation:
    """Test that orchestrator degrades gracefully when source circuit is open."""

    @pytest.mark.asyncio
    async def test_standard_degrades_when_tavily_circuit_open(self):
        """STANDARD query still returns Exa results if Tavily circuit is open."""
        exa = ExaSource(api_key="test")
        exa._client = _success_http_client({
            "results": [{"url": "https://ex.com/1", "title": "T", "text": "C", "score": 0.9}]
        })

        tavily = TavilySource(api_key="test")
        # Force tavily circuit open
        tavily._circuit_breaker._state = CircuitState.OPEN
        tavily._circuit_breaker._opened_at = time.monotonic()

        from intel.orchestrator import IntelOrchestrator

        orchestrator = IntelOrchestrator(exa=exa, tavily=tavily)
        result = await orchestrator.gather_intel("test", depth="STANDARD")

        # Should still have Exa results despite Tavily being down
        assert len(result.sources) > 0
        assert all(s.source_name == "exa" for s in result.sources)

        await orchestrator.close()
