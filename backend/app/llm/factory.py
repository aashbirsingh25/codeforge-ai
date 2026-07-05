import os
from app.llm.providers.base import BaseLLMProvider
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider

class ProviderFactory:
    """
    Factory class responsible for instantiating LLM providers with credentials loaded from environment variables.
    """
    
    @staticmethod
    def get_provider(provider_name: str) -> BaseLLMProvider:
        name = provider_name.lower().strip()
        if name == "gemini":
            api_key = os.getenv("GEMINI_API_KEY")
            return GeminiProvider(api_key=api_key)
        elif name == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            return OpenAIProvider(api_key=api_key)
        else:
            raise ValueError(f"Unknown or unsupported LLM provider: '{provider_name}'")
