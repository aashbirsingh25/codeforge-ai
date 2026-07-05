from app.core.exceptions import CodeForgeException


class LLMException(CodeForgeException):
    """Base exception for all LLM provider errors."""
    def __init__(self, message: str, original_exception: Exception | None = None, provider: str | None = None):
        self.message = message
        self.original_exception = original_exception
        self.provider = provider
        super().__init__(message)


class LLMAuthenticationException(LLMException):
    """Raised when authentication credentials (API key) are invalid or expired."""
    def __init__(self, message: str, original_exception: Exception | None = None, provider: str | None = None):
        super().__init__(message, original_exception, provider)
        self.status_code = 401


class LLMRateLimitException(LLMException):
    """Raised when rate limits are exceeded or API quota is exhausted."""
    def __init__(self, message: str, original_exception: Exception | None = None, provider: str | None = None):
        super().__init__(message, original_exception, provider)
        self.status_code = 429


class LLMTimeoutException(LLMException):
    """Raised when the connection to the provider times out."""
    def __init__(self, message: str, original_exception: Exception | None = None, provider: str | None = None):
        super().__init__(message, original_exception, provider)
        self.status_code = 504


class LLMProviderUnavailableException(LLMException):
    """Raised when the LLM service is offline or unreachable."""
    def __init__(self, message: str, original_exception: Exception | None = None, provider: str | None = None):
        super().__init__(message, original_exception, provider)
        self.status_code = 503


class LLMUnsupportedModelException(LLMException):
    """Raised when a requested model is invalid or unsupported."""
    def __init__(self, message: str, original_exception: Exception | None = None, provider: str | None = None):
        super().__init__(message, original_exception, provider)
        self.status_code = 400


class LLMInvalidRequestException(LLMException):
    """Raised when request parameters are invalid or formatting is bad."""
    def __init__(self, message: str, original_exception: Exception | None = None, provider: str | None = None):
        super().__init__(message, original_exception, provider)
        self.status_code = 400
