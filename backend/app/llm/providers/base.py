from abc import ABC, abstractmethod
from typing import AsyncGenerator, List
from app.llm.schemas import ChatCompletionRequest, ChatCompletionResponse

class BaseLLMProvider(ABC):
    """
    Abstract Base Class defining the contract for all LLM providers in CodeForge AI.
    """
    
    @abstractmethod
    async def generate(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """
        Send a chat completion request to the provider and return a static response.
        """
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
