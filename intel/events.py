"""Async event bus for inter-module communication.

Implements the EventEnvelope schema from docs/interfaces/events.md.
Supports fire-and-forget emission with async subscriber callbacks.
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from collections.abc import AsyncGenerator, Callable, Coroutine
from typing import Any

import structlog

from intel.types import Timestamp

log = structlog.get_logger(__name__)

# Type alias for event handler callbacks
EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class EventEnvelope:
    """Canonical event wrapper used for all inter-module events."""

    __slots__ = (
        "event_id",
        "event_type",
        "timestamp",
        "source_module",
        "correlation_id",
        "payload",
    )

    def __init__(
        self,
        event_type: str,
        payload: dict[str, Any],
        source_module: str = "",
        correlation_id: str = "",
    ) -> None:
        self.event_id = str(uuid.uuid4())
        self.event_type = event_type
        self.timestamp = Timestamp.now()
        self.source_module = source_module
        self.correlation_id = correlation_id
        self.payload = payload

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSON transport."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": {
                "unix_nanos": self.timestamp.unix_nanos,
                "iso8601": self.timestamp.iso8601,
            },
            "source_module": self.source_module,
            "correlation_id": self.correlation_id,
            "payload": self.payload,
        }


class EventBus:
    """Singleton-style async event bus.

    Supports:
    - Fire-and-forget emission
    - Named handler subscriptions
    - SSE streaming via async generator
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._sse_queues: list[asyncio.Queue[EventEnvelope]] = []
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Register a handler for a specific event type."""
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Remove a handler for a specific event type."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    async def emit(
        self,
        event_type: str,
        payload: dict[str, Any],
        source_module: str = "",
        correlation_id: str = "",
    ) -> EventEnvelope:
        """Emit an event to all registered handlers and SSE subscribers.

        Fire-and-forget: handler exceptions are logged but do not propagate.
        """
        envelope = EventEnvelope(
            event_type=event_type,
            payload=payload,
            source_module=source_module,
            correlation_id=correlation_id,
        )

        log.info(
            "Event emitted",
            event_type=event_type,
            event_id=envelope.event_id,
            correlation_id=correlation_id,
        )

        # Dispatch to handlers
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                await handler(envelope.to_dict())
            except Exception:
                log.exception(
                    "Event handler failed",
                    event_type=event_type,
                    event_id=envelope.event_id,
                    handler=getattr(handler, "__qualname__", repr(handler)),
                )

        # Push to SSE queues
        async with self._lock:
            for queue in self._sse_queues:
                try:
                    queue.put_nowait(envelope)
                except asyncio.QueueFull:
                    log.warning("SSE queue full, dropping event", event_id=envelope.event_id)

        return envelope

    async def sse_subscribe(self) -> AsyncGenerator[EventEnvelope, None]:
        """Subscribe to all events as an async generator (for SSE streaming)."""
        queue: asyncio.Queue[EventEnvelope] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._sse_queues.append(queue)
        try:
            while True:
                envelope = await queue.get()
                yield envelope
        finally:
            async with self._lock:
                self._sse_queues.remove(queue)

    async def sse_unsubscribe_all(self) -> None:
        """Remove all SSE subscribers."""
        async with self._lock:
            self._sse_queues.clear()


# Module-level singleton
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus singleton."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


def reset_event_bus() -> None:
    """Reset the global event bus (for testing)."""
    global _event_bus
    _event_bus = None
