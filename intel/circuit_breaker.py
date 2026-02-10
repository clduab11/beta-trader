"""Circuit breaker pattern for downstream service resilience.

Implements the three-state circuit breaker from docs/interfaces/errors.md:
- CLOSED: Normal operation, failures counted
- OPEN: Requests blocked, waiting for timeout
- HALF_OPEN: Probing with single test request

Configuration per service category:
- Intel APIs (Exa, Tavily, Firecrawl): 3 failures / 60s window, open 60s
- OpenRouter (per model): 3 failures / 30s window, open 60s
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import TYPE_CHECKING, TypeVar

import structlog
from pydantic import BaseModel, Field

from intel.errors import CircuitOpenError
from intel.events import get_event_bus

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

log = structlog.get_logger(__name__)
T = TypeVar("T")


class CircuitState(StrEnum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerConfig(BaseModel):
    """Configuration for a circuit breaker instance."""

    failure_threshold: int = Field(default=3, ge=1, description="Failures before opening")
    timeout_seconds: float = Field(default=60.0, gt=0, description="How long OPEN state lasts")
    half_open_max_calls: int = Field(default=1, ge=1, description="Test calls in HALF_OPEN")
    failure_window_seconds: float = Field(
        default=60.0, gt=0, description="Window for counting failures"
    )


# Pre-configured configs per service category
INTEL_API_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    timeout_seconds=60.0,
    half_open_max_calls=1,
    failure_window_seconds=60.0,
)

OPENROUTER_CONFIG = CircuitBreakerConfig(
    failure_threshold=3,
    timeout_seconds=60.0,
    half_open_max_calls=1,
    failure_window_seconds=30.0,
)


class CircuitBreaker:
    """Three-state circuit breaker for downstream service calls.

    Usage:
        cb = CircuitBreaker("exa", config=INTEL_API_CONFIG)
        result = await cb.call(lambda: httpx_client.get(url))
    """

    def __init__(
        self,
        service_name: str,
        config: CircuitBreakerConfig | None = None,
        source_module: str = "",
    ) -> None:
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()
        self.source_module = source_module

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._failure_timestamps: list[float] = []
        self._opened_at: float = 0.0
        self._half_open_calls: int = 0

    @property
    def state(self) -> CircuitState:
        """Current circuit breaker state (may auto-transition from OPEN to HALF_OPEN)."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._opened_at
            if elapsed >= self.config.timeout_seconds:
                self._transition_to(CircuitState.HALF_OPEN)
        return self._state

    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        return self._state == CircuitState.OPEN

    def _transition_to(self, new_state: CircuitState, query_id: str | None = None) -> None:
        """Transition to a new state, emitting an event."""
        old_state = self._state
        if old_state == new_state:
            return

        self._state = new_state
        log.info(
            "Circuit breaker state changed",
            service=self.service_name,
            from_state=old_state,
            to_state=new_state,
            query_id=query_id,
        )

        # Emit event (fire-and-forget, non-blocking)
        event_bus = get_event_bus()
        payload = {
            "source_name": self.service_name,
            "state": new_state.value,
            "previous_state": old_state.value,
            "query_id": query_id,
        }
        if new_state == CircuitState.OPEN:
            payload["reopens_in_seconds"] = self.config.timeout_seconds
        # Schedule event emission without blocking
        import asyncio

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                event_bus.emit(
                    event_type="circuit_breaker_state_changed",
                    payload=payload,
                    source_module=self.source_module or f"intel.{self.service_name}",
                )
            )
        except RuntimeError:
            pass  # No event loop running (e.g., in sync test context)

        # Reset counters on state transitions
        if new_state == CircuitState.CLOSED:
            self._failure_count = 0
            self._failure_timestamps.clear()
            self._half_open_calls = 0

    async def call(self, func: Callable[[], Awaitable[T]], query_id: str | None = None) -> T:
        """Execute a function protected by the circuit breaker.

        Args:
            func: Async function to execute.
            query_id: Optional ID of the query triggering this call.

        Raises:
            CircuitOpenError: If the circuit is OPEN.
            Exception: Whatever func raises (counted as failure).
        """
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(
                service=self.service_name,
                retry_after=self.config.timeout_seconds,
            )

        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                raise CircuitOpenError(
                    service=self.service_name,
                    retry_after=1.0,  # Short retry for half-open race
                )
            self._half_open_calls += 1

        try:
            result = await func()
            self._record_success()
            return result
        except Exception:
            self._record_failure(query_id)
            raise

    def _record_success(self) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.CLOSED)

    def _record_failure(self, query_id: str | None = None) -> None:
        """Handle failed call."""
        now = time.monotonic()
        self._failure_timestamps.append(now)
        
        # Prune old failures
        self._failure_timestamps = [
            t for t in self._failure_timestamps
            if now - t <= self.config.failure_window_seconds
        ]
        
        self._failure_count = len(self._failure_timestamps)

        if self._state == CircuitState.HALF_OPEN:
            # Single failure in HALF_OPEN trips back to OPEN
            self._transition_to(CircuitState.OPEN, query_id)
            self._opened_at = now
        elif (
            self._state == CircuitState.CLOSED
            and self._failure_count >= self.config.failure_threshold
        ):
            self._transition_to(CircuitState.OPEN, query_id)
            self._opened_at = now

        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0

    def _prune_old_failures(self) -> None:
        """Remove failures outside the rolling window."""
        cutoff = time.monotonic() - self.config.failure_window_seconds
        self._failure_timestamps = [t for t in self._failure_timestamps if t >= cutoff]
        self._failure_count = len(self._failure_timestamps)

    def _record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        now = time.monotonic()
        self._failure_timestamps.append(now)
        self._prune_old_failures()

        if self._state == CircuitState.HALF_OPEN:
            # Failed probe → back to OPEN
            self._opened_at = time.monotonic()
            self._transition_to(CircuitState.OPEN)
        elif self._failure_count >= self.config.failure_threshold:
            self._opened_at = time.monotonic()
            self._transition_to(CircuitState.OPEN)

    def _record_success(self) -> None:
        """Record a success; may close the circuit from HALF_OPEN."""
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to(CircuitState.CLOSED)
        elif self._state == CircuitState.CLOSED:
            # Optionally decay failure count on success
            self._prune_old_failures()

    async def call(self, fn: Callable[[], Awaitable[T]]) -> T:
        """Execute fn through the circuit breaker.

        Raises CircuitOpenError if the circuit is OPEN.
        """
        current_state = self.state  # Triggers auto-transition if needed

        if current_state == CircuitState.OPEN:
            remaining = self.config.timeout_seconds - (time.monotonic() - self._opened_at)
            raise CircuitOpenError(
                message=f"Circuit open for {self.service_name} ({remaining:.1f}s remaining)",
                source_module=self.source_module or f"intel.{self.service_name}",
                service_name=self.service_name,
                reopens_in_seconds=max(0.0, remaining),
            )

        if current_state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls > self.config.half_open_max_calls:
                raise CircuitOpenError(
                    message=f"Circuit half-open probe limit reached for {self.service_name}",
                    source_module=self.source_module or f"intel.{self.service_name}",
                    service_name=self.service_name,
                )

        try:
            result = await fn()
            self._record_success()
            return result
        except Exception:
            self._record_failure()
            raise

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED."""
        self._transition_to(CircuitState.CLOSED)
