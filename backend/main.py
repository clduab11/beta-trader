import asyncio
import json
import logging
import sys
import time
import traceback
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import structlog
from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

from backend.depth import get_depth_recommender
from backend.middleware import CorrelationIdMiddleware, LoggingMiddleware
from backend.models import (
    DepthRequest,
    DepthResponse,
    ErrorResponse,
    IntelRequest,
    IntelResponse,
    LLMTestRequest,
    LLMTestResponse,
    SettingsResponse,
    SettingsUpdateRequest,
    CouncilExportRequest,
    CouncilExportResponse,
)
from backend.settings import Settings, get_settings_manager
from backend.sse import get_sse_emitter
from council.store import KnowledgeStore
from council.manager import CouncilManager
from intel.events import get_event_bus
from intel.orchestrator import IntelOrchestrator
from intel.types import IntelResult
from routing.openrouter.client import OpenRouterClient

# Configure Structlog
def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Redirect standard logging to structlog
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

setup_logging()
log = structlog.get_logger(__name__)

# Singletons
intel_orchestrator: IntelOrchestrator | None = None
openrouter_client: OpenRouterClient | None = None
knowledge_store: KnowledgeStore | None = None
council_manager: CouncilManager | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global intel_orchestrator, openrouter_client, knowledge_store, council_manager
    
    log.info("system_startup")
    
    # Init singletons
    try:
        intel_orchestrator = IntelOrchestrator()
    except Exception as e:
        log.error("intel_orchestrator_init_failed", error=str(e))

    try:
        openrouter_client = OpenRouterClient()
    except Exception as e:
        log.error("openrouter_client_init_failed", error=str(e))
        
    knowledge_store = KnowledgeStore()
    council_manager = CouncilManager()
    
    # Init Knowledge Store connection
    try:
        await knowledge_store.connect()
    except Exception as e:
        log.error("knowledge_store_connect_failed", error=str(e))

    # Init Council Manager connection
    try:
        await council_manager.connect()
    except Exception as e:
        log.error("council_manager_connect_failed", error=str(e))
    
    # Warm up settings and SSE
    get_settings_manager()
    get_sse_emitter()
    get_event_bus()
    
    yield
    
    if knowledge_store:
        await knowledge_store.close()
    if council_manager and hasattr(council_manager, "client") and council_manager.client:
        await council_manager.client.aclose()
        
    log.info("system_shutdown")

app = FastAPI(
    title="Beta-Trader API",
    description="Backend API for Beta-Trader Platform",
    version="0.1.0",
    lifespan=lifespan,
    responses={500: {"model": ErrorResponse}}
)

# Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    show_traceback = request.query_params.get("traceback", "false").lower() == "true"
    
    error_content = {
        "error": str(exc),
        "request_id": request_id,
        "traceback": traceback.format_exc() if show_traceback else None
    }
    
    if not show_traceback:
        del error_content["traceback"]
        
    return JSONResponse(
        status_code=500,
        content=error_content
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "request_id": request_id}
    )

# Endpoints

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "beta-trader-backend"}

@app.get("/api/events")
async def sse_events(session_id: str = Query(..., description="Client Session ID")):
    """SSE endpoint for session-scoped events."""
    emitter = get_sse_emitter()
    
    async def generator():
        async for msg in emitter.subscribe(session_id):
            yield msg
            
    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@app.post("/api/intel/query", response_model=IntelResponse)
async def query_intel(request: IntelRequest):
    if not intel_orchestrator:
        raise HTTPException(status_code=503, detail="Intel Orchestrator not ready")
    
    try:
        result = await intel_orchestrator.gather_intel(request.query, request.depth)
        return IntelResponse(result=result, cost=result.total_cost_usd) 
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recommend-depth", response_model=DepthResponse)
async def recommend_depth(request: DepthRequest):
    recommender = get_depth_recommender()
    depth = recommender.recommend(request.query)
    return DepthResponse(depth=depth)

@app.post("/api/openrouter/test", response_model=LLMTestResponse)
async def test_llm(request: LLMTestRequest):
    if not openrouter_client:
        raise HTTPException(status_code=503, detail="OpenRouter Client not ready")
        
    start = time.monotonic()
    try:
        # Client handles model rotation internally
        result = await openrouter_client.complete(
            prompt=request.prompt,
            task_type="coding" # using generic task type
        )
        response_text = result.content
    except Exception as e:
        # Fallback/Error handled
        raise HTTPException(status_code=500, detail=f"LLM Error: {e}")
        
    duration = (time.monotonic() - start) * 1000
    return LLMTestResponse(response=response_text, latency_ms=duration)

@app.get("/api/settings", response_model=SettingsResponse)
async def get_app_settings():
    manager = get_settings_manager()
    return SettingsResponse(settings=manager.get_settings().model_dump(by_alias=True))

@app.post("/api/settings/save", response_model=SettingsResponse)
async def update_settings_endpoint(request: SettingsUpdateRequest):
    manager = get_settings_manager()
    new_settings = manager.update_settings(request.settings)
    return SettingsResponse(settings=new_settings.model_dump(by_alias=True))

@app.post("/api/settings/test")
async def test_settings():
    # Verify connections
    checks = {
        "redis": knowledge_store._client is not None if knowledge_store else False,
        "openai": False, 
        "openrouter": openrouter_client is not None,
        "intel": intel_orchestrator is not None,
        "council": council_manager and council_manager.client is not None
    }
    return checks

@app.post("/api/council/export", response_model=CouncilExportResponse)
async def export_council(request: CouncilExportRequest):
    if not council_manager:
        raise HTTPException(status_code=503, detail="Council Manager not ready")
    
    try:
        # Reconstruct IntelResult from dict
        intel_result = IntelResult(**request.intel_result)
        record = await council_manager.export_result(
            result=intel_result,
            tags=request.tags,
            metadata=request.metadata
        )
        return CouncilExportResponse(record_id=str(record.id), query_id=record.query_id)
    except Exception as e:
        log.error("Export failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/council")
async def search_council(q: str = "*", limit: int = 10, mode: str = "keyword"):
    if not council_manager:
        raise HTTPException(status_code=503, detail="Council Manager not ready")
    
    try:
        if mode == "semantic":
            records = await council_manager.search_semantic(q, limit)
        else:
            records = await council_manager.search_keyword(q, limit)
            
        return {"total": len(records), "docs": records}
    except Exception as e:
        log.warning(f"Search failed: {e}")
        return {"total": 0, "docs": [], "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
