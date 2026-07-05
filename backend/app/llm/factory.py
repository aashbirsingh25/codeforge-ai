import os
from app.llm.providers.base import BaseLLMProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider

class ProviderFactory:
    """
    Factory class responsible for instantiating LLM providers using Settings configuration.
    """
    
    @staticmethod
    def get_provider(provider_name: str) -> BaseLLMProvider:
        name = provider_name.lower().strip()
        if name == "gemini":
            return GeminiProvider()
        elif name == "openai":
            return OpenAIProvider()
        else:
            raise ValueError(f"Unknown or unsupported LLM provider: '{provider_name}'")
