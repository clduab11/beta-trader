"""Unit tests for the event bus system."""

import asyncio
from unittest.mock import AsyncMock

import pytest

from intel.events import EventBus, EventEnvelope, get_event_bus, reset_event_bus


@pytest.fixture(autouse=True)
def _reset_bus():
    """Reset the global event bus before each test."""
    reset_event_bus()
    yield
    reset_event_bus()


class TestEventEnvelope:
    def test_creation(self):
        env = EventEnvelope(
            event_type="IntelGathered",
            payload={"query_id": "test"},
            source_module="intel.orchestrator",
            correlation_id="req-123",
        )
        assert env.event_type == "IntelGathered"
        assert env.payload["query_id"] == "test"
        assert env.event_id  # UUID generated
        assert env.timestamp.unix_nanos > 0

    def test_to_dict(self):
        env = EventEnvelope(
            event_type="SourceQueried",
            payload={"source": "exa"},
            source_module="intel.exa",
        )
        d = env.to_dict()
        assert d["event_type"] == "SourceQueried"
        assert d["payload"]["source"] == "exa"
        assert "timestamp" in d
        assert "event_id" in d


class TestEventBus:
    @pytest.mark.asyncio
    async def test_emit_calls_handler(self):
        bus = EventBus()
        handler = AsyncMock()
        bus.subscribe("TestEvent", handler)

        await bus.emit("TestEvent", {"key": "value"}, source_module="test")

        handler.assert_called_once()
        call_args = handler.call_args[0][0]
        assert call_args["event_type"] == "TestEvent"
        assert call_args["payload"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_emit_multiple_handlers(self):
        bus = EventBus()
        handler1 = AsyncMock()
        handler2 = AsyncMock()
        bus.subscribe("TestEvent", handler1)
        bus.subscribe("TestEvent", handler2)

        await bus.emit("TestEvent", {})

        handler1.assert_called_once()
        handler2.assert_called_once()

    @pytest.mark.asyncio
    async def test_emit_wrong_event_type(self):
        bus = EventBus()
        handler = AsyncMock()
        bus.subscribe("TypeA", handler)

        await bus.emit("TypeB", {})

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_handler_exception_does_not_propagate(self):
        bus = EventBus()
        bad_handler = AsyncMock(side_effect=Exception("boom"))
        good_handler = AsyncMock()
        bus.subscribe("TestEvent", bad_handler)
        bus.subscribe("TestEvent", good_handler)

        # Should not raise
        await bus.emit("TestEvent", {})

        bad_handler.assert_called_once()
        good_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        handler = AsyncMock()
        bus.subscribe("TestEvent", handler)
        bus.unsubscribe("TestEvent", handler)

        await bus.emit("TestEvent", {})

        handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_sse_subscribe(self):
        bus = EventBus()
        received: list[EventEnvelope] = []

        async def consumer():
            async for envelope in bus.sse_subscribe():
                received.append(envelope)
                if len(received) >= 2:
                    break

        # Start consumer in background
        task = asyncio.create_task(consumer())

        # Give consumer time to register
        await asyncio.sleep(0.05)

        await bus.emit("Event1", {"n": 1})
        await bus.emit("Event2", {"n": 2})

        await asyncio.wait_for(task, timeout=2.0)

        assert len(received) == 2
        assert received[0].event_type == "Event1"
        assert received[1].event_type == "Event2"

    @pytest.mark.asyncio
    async def test_emit_returns_envelope(self):
        bus = EventBus()
        envelope = await bus.emit("TestEvent", {"data": 42}, correlation_id="c-1")

        assert isinstance(envelope, EventEnvelope)
        assert envelope.event_type == "TestEvent"
        assert envelope.correlation_id == "c-1"


class TestEventBusSingleton:
    def test_get_event_bus_returns_same_instance(self):
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_reset_creates_new_instance(self):
        bus1 = get_event_bus()
        reset_event_bus()
        bus2 = get_event_bus()
        assert bus1 is not bus2
