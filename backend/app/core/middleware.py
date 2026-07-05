import time
import uuid
import logging
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("app.core.middleware")


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
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
    app.add_middleware(LoggingMiddleware)
