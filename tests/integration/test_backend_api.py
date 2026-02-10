import json
import asyncio
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from backend.main import app
from intel.events import get_event_bus, reset_event_bus

@pytest.fixture(autouse=True)
def clean_event_bus():
    reset_event_bus()
    yield
    reset_event_bus()

@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok", "service": "beta-trader-backend"}

@pytest.mark.asyncio
async def test_sse_endpoint():
    """Test that the SSE endpoint streams events emitted to the bus."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:  # noqa: SIM117
        
        session_id = str(uuid.uuid4())
        
        # Test connection with session_id
        async with ac.stream("GET", f"/api/events?session_id={session_id}") as response:
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/event-stream"
            
            bus = get_event_bus()
            test_payload = {"msg": "hello sse"}
            
            # Start reading in a background task
            async def read_events():
                events = []
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = json.loads(line[6:])
                        events.append(data)
                        if data.get("payload", {}).get("type") == "test_event": # Match nested payload structure if wrapped
                             # The bus emit wrapper adds "payload" key, and "event_type".
                            return events
                        if data.get("event_type") == "test_event":
                            return events
                return events
            
            reader_task = asyncio.create_task(read_events())
            
            # Allow time for subscription
            await asyncio.sleep(0.5)
            
            # Emit event 
            await bus.emit("test_event", {"type": "test_event", "payload": test_payload})
            
            try:
                events = await asyncio.wait_for(reader_task, timeout=2.0)
                # First event is connection info
                assert events[0]["type"] == "connected"
                assert events[0]["session_id"] == session_id
                
                # Second should be our emitted event
                if len(events) > 1:
                    assert events[1]["event_type"] == "test_event"
                else:
                    pytest.fail("Did not receive emitted event")
                
            except asyncio.TimeoutError:
                pytest.fail("Timeout waiting for SSE event")
            except Exception as e:
                pytest.fail(f"SSE test failed: {e}")

@pytest.mark.asyncio
async def test_depth_recommendation():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/api/depth", json={"query": "analyze the detailed financials"})
        assert response.status_code == 200
        data = response.json()
        assert data["depth"] == "DEEP"
        
        response = await ac.post("/api/depth", json={"query": "what is the price"})
        assert response.status_code == 200
        data = response.json()
        assert data["depth"] == "SHALLOW"

@pytest.mark.asyncio
async def test_settings_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/settings")
        assert response.status_code == 200
        assert "app_env" in response.json()["settings"]
        
        response = await ac.post("/api/settings/test")
        assert response.status_code == 200
        checks = response.json()
        assert "redis" in checks
