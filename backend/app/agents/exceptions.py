from fastapi import status
from app.core.exceptions import CodeForgeException

class AgentExecutionError(CodeForgeException):
    """Base exception for all agent execution errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(message, status_code=status_code)

class AgentDependencyError(AgentExecutionError):
    """Raised when task execution fails due to dependency errors or cycles."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)

class AgentToolError(AgentExecutionError):
    """Raised when an error occurs during tool execution within the agent loop."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)

class AgentRetryExceededError(AgentExecutionError):
    """Raised when a task has failed and exceeded the maximum allowed retries."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_408_REQUEST_TIMEOUT)
