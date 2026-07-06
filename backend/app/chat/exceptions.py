from fastapi import status
from app.core.exceptions import CodeForgeException

class ChatException(CodeForgeException):
    """Base exception for Conversational AI Assistant"""
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        super().__init__(message, status_code)

class ChatProviderException(ChatException):
    """Exception raised when LLM provider completions fail"""
    def __init__(self, message: str):
        super().__init__(message, status_code=status.HTTP_502_BAD_GATEWAY)
