from fastapi import status
from app.core.exceptions import CodeForgeException

class MemoryException(CodeForgeException):
    """Base exception for Memory & Context Engine"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(message, status_code)

class MemoryNotFoundException(MemoryException):
    """Exception raised when a memory entry is not found"""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_404_NOT_FOUND)

class MemoryPersistenceException(MemoryException):
    """Exception raised when memory persistence fails"""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

class MemoryValidationException(MemoryException):
    """Exception raised when memory validation fails"""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
