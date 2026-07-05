from fastapi import status
from app.core.exceptions import CodeForgeException


class PlanningError(CodeForgeException):
    """Base exception for all planning engine errors."""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(message, status_code=status_code)


class PlanningParseError(PlanningError):
    """Raised when the LLM response cannot be parsed as valid JSON or fails schema matching."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class PlanningValidationError(PlanningError):
    """Raised when the parsed execution plan violates custom validation/consistency rules."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class PlanningStrategyError(PlanningError):
    """Raised when strategy selection or execution parameters are invalid."""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_400_BAD_REQUEST)
