import time
import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        # Bind context for structlog
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        
        request.state.request_id = request_id
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.monotonic()
        
        access_logger = structlog.get_logger("api.access")
        
        try:
            response = await call_next(request)
            process_time = time.monotonic() - start_time
            
            access_logger.info(
                "http_access",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=round(process_time * 1000, 2),
                request_id=request.state.request_id
            )
            return response
        except Exception as exc:
            process_time = time.monotonic() - start_time
            access_logger.error(
                "http_error",
                method=request.method,
                path=request.url.path,
                error=str(exc),
                duration_ms=round(process_time * 1000, 2),
                request_id=request.state.request_id
            )
            # Re-raise so the ExceptionHandler can catch it or default
            raise exc
