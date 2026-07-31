from abc import ABC, abstractmethod
from typing import AsyncGenerator, List
from app.llm.schemas import ChatCompletionRequest, ChatCompletionResponse

class BaseLLMProvider(ABC):
    """
    Abstract Base Class defining the contract for all LLM providers in CodeForge AI.
    """
    
    async def generate(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """
        Send a chat completion request to the provider and return a static response.
        Checks and sets Redis cache for deterministic requests (temperature == 0).
        """
        from app.llm.cache import llm_cache
        
        cached_response = await llm_cache.get(request)
        if cached_response is not None:
            return cached_response

        response = await self._generate(request)

        await llm_cache.set(request, response)
        return response

    @abstractmethod
    async def _generate(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Subclass implementation of LLM generation."""
        pass

    @abstractmethod
    async def generate_stream(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        """
        Send a chat completion request and yield response chunks as they become available.
        """
        # Yield statements are handled inside subclasses
        yield ""

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Validate credentials and service health. Returns True if operational, False otherwise.
        """
        pass

    @abstractmethod
    def list_models(self) -> List[str]:
        """
        List all model identifiers natively supported by this provider.
        """
        pass
