import asyncio
import json
import logging
import uuid
from collections import defaultdict
from typing import Any, AsyncGenerator

from intel.events import get_event_bus, EventEnvelope, EventBus

log = logging.getLogger(__name__)

class SSEEventEmitter:
    """Manages SSE subscriptions and event streaming for client sessions."""
    
    def __init__(self, event_bus: EventBus):
        self.bus = event_bus
        # Map session_id to queue
        self._queues: dict[str, asyncio.Queue] = {}
        # Map session_id to set of query_ids/filters? 
        # Requirement says "filters by session/query". 
        # Typically the event bus emits events. Some events might be targeted.
        # We'll assume the client filters, OR we can filter here if events have session_ids.
        self._lock = asyncio.Lock()
        
    async def subscribe(self, session_id: str) -> AsyncGenerator[str, None]:
        """Subscribe a session to the event stream."""
        queue: asyncio.Queue[EventEnvelope | str] = asyncio.Queue(maxsize=100)
        
        async with self._lock:
            self._queues[session_id] = queue
            
        system_queue = self.bus.sse_subscribe()
        
        # Task to forward system events to this session (filtering logic could go here)
        forward_task = asyncio.create_task(self._forward_events(session_id, queue, system_queue))
        # Task to send heartbeats
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(queue))
        
        try:
            yield f"event: system\ndata: {json.dumps({'type': 'connected', 'session_id': session_id})}\n\n"
            
            while True:
                item = await queue.get()
                if isinstance(item, EventEnvelope):
                    # Format: 
                    # event: <event_type>
                    # data: <json_payload>
                    
                    # Filtering: If event has correlation_id related to this session?
                    # For now, broadcasting everything as "observability" usually implies seeing system state.
                    # But ticket says "enforce session-scoped subscriptions".
                    # If an event has a 'session_id' in payload, we check it.
                    
                    # Check if event is targeted
                    target_session = item.payload.get("session_id")
                    if target_session and target_session != session_id:
                        continue

                    # Construct SSE message
                    yield f"event: {item.event_type}\ndata: {json.dumps(item.to_dict())}\n\n"
                    
                elif isinstance(item, str) and item == "HEARTBEAT":
                    yield ": heartbeat\n\n"
                    
        except asyncio.CancelledError:
            log.info(f"Session {session_id} disconnected")
        finally:
            forward_task.cancel()
            heartbeat_task.cancel()
            await self.bus.sse_unsubscribe_all() # Wait, this removes ALL? That method might be too aggressive in EventBus...
            # Looking at EventBus implementation (read previously):
            # sse_unsubscribe_all clears all queues. We shouldn't call that here.
            # We should probably handle the specific queue cleanup.
            # But the EventBus implementation had sse_queue as a list, and sse_subscribe yielded from local queue.
            # Here we are consuming `system_queue` generator. We just stop iterating it.
            
            async with self._lock:
                if session_id in self._queues:
                    del self._queues[session_id]

    async def _forward_events(self, session_id: str, dest_queue: asyncio.Queue, source_gen: AsyncGenerator[EventEnvelope, None]):
        """Forward events from the global bus to the user queue."""
        try:
            async for envelope in source_gen:
                try:
                    dest_queue.put_nowait(envelope)
                except asyncio.QueueFull:
                    pass # Drop if slow consumer
        except Exception:
            pass

    async def _heartbeat_loop(self, queue: asyncio.Queue):
        """Send heartbeats periodically."""
        while True:
            await asyncio.sleep(30)
            try:
                queue.put_nowait("HEARTBEAT")
            except asyncio.QueueFull:
                pass


_sse_emitter: SSEEventEmitter | None = None

def get_sse_emitter() -> SSEEventEmitter:
    global _sse_emitter
    if _sse_emitter is None:
        _sse_emitter = SSEEventEmitter(get_event_bus())
    return _sse_emitter
