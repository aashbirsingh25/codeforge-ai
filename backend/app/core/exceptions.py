from datetime import datetime, timezone
import traceback
import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.core.exceptions")


class CodeForgeException(Exception):
    """Base exception for CodeForge AI"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class WorkspaceException(CodeForgeException):
    """Security or operational errors related to the workspace directory"""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_403_FORBIDDEN)


def format_error_response(
    request: Request,
    exc: Exception,
    status_code: int,
    message: str,
    error_type: str | None = None,
    provider: str | None = None,
    details: str | None = None
) -> JSONResponse:
    """Standardizes error response payload schema across all routes and handlers."""
    err_type = error_type or exc.__class__.__name__
    request_id = getattr(request.state, "request_id", None)
    timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    
    error_body = {
        "type": err_type,
        "message": message,
    }
    if provider:
        error_body["provider"] = provider
    if details:
        error_body["details"] = details
    error_body["timestamp"] = timestamp
    if request_id:
        error_body["request_id"] = request_id
        
    return JSONResponse(
        status_code=status_code,
        content={"error": error_body}
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Registers centralized handlers to automatically format exceptions into standardized schemas."""
    
    @app.exception_handler(CodeForgeException)
    async def codeforge_exception_handler(request: Request, exc: CodeForgeException):
        provider = getattr(exc, "provider", None)
        status_code = getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        logger.error(
            f"CodeForge Error on {request.method} {request.url.path} | "
            f"Type: {exc.__class__.__name__} | Message: {exc.message} | Status: {status_code}"
        )
        
        return format_error_response(
            request=request,
            exc=exc,
            status_code=status_code,
            message=exc.message,
            provider=provider
        )

    @app.exception_handler(FileNotFoundError)
    async def filenotfound_exception_handler(request: Request, exc: FileNotFoundError):
        logger.error(f"FileNotFoundError on {request.method} {request.url.path}: {str(exc)}")
        return format_error_response(
            request=request,
            exc=exc,
            status_code=status.HTTP_404_NOT_FOUND,
            message=str(exc)
        )

    @app.exception_handler(PermissionError)
    async def permission_exception_handler(request: Request, exc: PermissionError):
        logger.error(f"PermissionError on {request.method} {request.url.path}: {str(exc)}")
        return format_error_response(
            request=request,
            exc=exc,
            status_code=status.HTTP_403_FORBIDDEN,
            message=str(exc)
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(f"HTTP Error on {request.method} {request.url.path}: {exc.detail} | Status: {exc.status_code}")
        return format_error_response(
            request=request,
            exc=exc,
            status_code=exc.status_code,
            message=exc.detail
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Validation Error on {request.method} {request.url.path}: {exc.errors()}")
        errors_summary = exc.errors()
        return format_error_response(
            request=request,
            exc=exc,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Request validation failed.",
            details=str(errors_summary)
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "N/A")
        endpoint = f"{request.method} {request.url.path}"
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        exc_type = exc.__class__.__name__
        tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        
        logger.error(
            f"Unhandled Exception on {endpoint} | Request ID: {request_id} | "
            f"Timestamp: {timestamp} | Type: {exc_type} | Message: {str(exc)}\n{tb}"
        )
        
        return format_error_response(
            request=request,
            exc=exc,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="An unexpected error occurred. Please contact system administrator."
        )
