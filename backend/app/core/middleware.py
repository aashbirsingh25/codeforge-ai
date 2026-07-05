import time
import logging
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(
                f"Request: {request.method} {request.url.path} - "
                f"Response: {response.status_code} ({duration:.4f}s)"
            )
            response.headers["X-Response-Time-Seconds"] = f"{duration:.4f}"
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Request Exception: {request.method} {request.url.path} - "
                f"Failed after {duration:.4f}s - Error: {str(e)}"
            )
            raise e

def register_middleware(app: FastAPI) -> None:
    app.add_middleware(LoggingMiddleware)
