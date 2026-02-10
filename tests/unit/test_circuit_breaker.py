"""Unit tests for the circuit breaker."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from intel.circuit_breaker import (
    INTEL_API_CONFIG,
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
)
from intel.errors import CircuitOpenError
from intel.events import reset_event_bus


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


class TestCircuitBreakerConfig:
    def test_defaults(self):
        cfg = CircuitBreakerConfig()
        assert cfg.failure_threshold == 3
        assert cfg.timeout_seconds == 60.0
        assert cfg.half_open_max_calls == 1

    def test_intel_api_config(self):
        assert INTEL_API_CONFIG.failure_threshold == 3
        assert INTEL_API_CONFIG.timeout_seconds == 60.0


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_closed_by_default(self):
        cb = CircuitBreaker("test", config=CircuitBreakerConfig(failure_threshold=3))
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed

    @pytest.mark.asyncio
    async def test_successful_call(self):
        cb = CircuitBreaker("test")
        fn = AsyncMock(return_value="ok")
        result = await cb.call(fn)
        assert result == "ok"
        fn.assert_called_once()

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        cfg = CircuitBreakerConfig(failure_threshold=3, failure_window_seconds=60.0)
        cb = CircuitBreaker("test", config=cfg)

        fn = AsyncMock(side_effect=Exception("fail"))

        for _ in range(3):
            with pytest.raises(Exception, match="fail"):
                await cb.call(fn)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_rejects_calls(self):
        cfg = CircuitBreakerConfig(failure_threshold=2, timeout_seconds=60.0)
        cb = CircuitBreaker("test", config=cfg)

        fn = AsyncMock(side_effect=Exception("fail"))
        for _ in range(2):
            with pytest.raises(Exception, match="fail"):
                await cb.call(fn)

        # Now open — should raise CircuitOpenError
        with pytest.raises(CircuitOpenError) as exc_info:
            await cb.call(AsyncMock())

        assert "test" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_transitions_to_half_open_after_timeout(self):
        cfg = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.1,  # Very short for test
            failure_window_seconds=60.0,
        )
        cb = CircuitBreaker("test", config=cfg)

        fn = AsyncMock(side_effect=RuntimeError("fail"))
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fn)

        assert cb._state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(0.15)

        # State check triggers auto-transition
        assert cb.state == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_half_open_success_closes(self):
        cfg = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.05,
            failure_window_seconds=60.0,
        )
        cb = CircuitBreaker("test", config=cfg)

        # Trip the breaker
        fail_fn = AsyncMock(side_effect=RuntimeError("fail"))
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail_fn)

        await asyncio.sleep(0.06)

        # Probe with success
        success_fn = AsyncMock(return_value="recovered")
        result = await cb.call(success_fn)
        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self):
        cfg = CircuitBreakerConfig(
            failure_threshold=2,
            timeout_seconds=0.05,
            failure_window_seconds=60.0,
        )
        cb = CircuitBreaker("test", config=cfg)

        # Trip the breaker
        fail_fn = AsyncMock(side_effect=RuntimeError("fail"))
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail_fn)

        await asyncio.sleep(0.06)

        # Probe with failure
        with pytest.raises(RuntimeError, match="fail"):
            await cb.call(fail_fn)

        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_reset(self):
        cfg = CircuitBreakerConfig(failure_threshold=2)
        cb = CircuitBreaker("test", config=cfg)

        fn = AsyncMock(side_effect=RuntimeError("fail"))
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fn)

        assert cb.state == CircuitState.OPEN
        cb.reset()
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_success_prunes_old_failures(self):
        cfg = CircuitBreakerConfig(
            failure_threshold=3,
            failure_window_seconds=0.05,
        )
        cb = CircuitBreaker("test", config=cfg)

        fail_fn = AsyncMock(side_effect=RuntimeError("fail"))
        # Two failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                await cb.call(fail_fn)

        # Wait for failure window to expire
        await asyncio.sleep(0.06)

        # Success should prune old failures
        success_fn = AsyncMock(return_value="ok")
        await cb.call(success_fn)

        # Should still be closed (old failures pruned)
        assert cb.state == CircuitState.CLOSED
