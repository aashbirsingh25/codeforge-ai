import time
import uuid
import logging
from typing import Dict, List
from fastapi import FastAPI, Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.metrics import metrics_tracker
from app.core.exceptions import format_error_response

logger = logging.getLogger("app.core.middleware")

class RateLimiter:
    def __init__(self, limit: int = 100, window_seconds: float = 60.0):
        self.limit = limit
        self.window_seconds = window_seconds
        self.history: Dict[str, List[float]] = {}

    def is_rate_limited(self, client_ip: str) -> bool:
        now = time.time()
        if client_ip not in self.history:
            self.history[client_ip] = []
        
        # Filter timestamps older than the window
        self.history[client_ip] = [t for t in self.history[client_ip] if now - t < self.window_seconds]
        
        if len(self.history[client_ip]) >= self.limit:
            return True
            
        self.history[client_ip].append(now)
        return False

rate_limiter = RateLimiter(
    limit=settings.RATE_LIMIT_CALLS, 
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS
)

class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path.endswith("/health"):
            return await call_next(request)
            
        client_ip = request.client.host if request.client else "unknown"
        
        rate_limiter.limit = settings.RATE_LIMIT_CALLS
        rate_limiter.window_seconds = settings.RATE_LIMIT_WINDOW_SECONDS
        
        if rate_limiter.is_rate_limited(client_ip):
            exc = HTTPException(status_code=429, detail="Rate limit exceeded. Too many requests.")
            return format_error_response(
                request=request,
                exc=exc,
                status_code=429,
                message="Rate limit exceeded. Please try again later.",
                error_type="RateLimitExceeded"
            )
            
        return await call_next(request)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        metrics_tracker.track_request()
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(
                f"Request ID: {request_id} | Request: {request.method} {request.url.path} - "
                f"Response: {response.status_code} ({duration:.4f}s)"
            )
            response.headers["X-Response-Time-Seconds"] = f"{duration:.4f}"
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request ID: {request_id} | Request Exception: {request.method} {request.url.path} - "
                f"Failed after {duration:.4f}s - Error: {str(e)}"
            )
            raise e

def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(LoggingMiddleware)
