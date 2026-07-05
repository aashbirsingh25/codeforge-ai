class LLMException(Exception):
    """Base exception for all LLM provider errors."""
    def __init__(self, message: str, original_exception: Exception | None = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)

class LLMAuthenticationException(LLMException):
    """Raised when authentication credentials (API key) are invalid or expired."""
    pass

class LLMRateLimitException(LLMException):
    """Raised when rate limits are exceeded or API quota is exhausted."""
    pass

class LLMTimeoutException(LLMException):
    """Raised when the connection to the provider times out."""
    pass

class LLMProviderUnavailableException(LLMException):
    """Raised when the LLM service is offline or unreachable."""
    pass

class LLMUnsupportedModelException(LLMException):
    """Raised when a requested model is invalid or unsupported."""
    pass

class LLMInvalidRequestException(LLMException):
    """Raised when request parameters are invalid or formatting is bad."""
    pass
