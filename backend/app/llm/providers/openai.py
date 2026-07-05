import functools
from typing import AsyncGenerator, List, Any, Dict
from openai import AsyncOpenAI
import openai

from app.llm.providers.base import BaseLLMProvider
from app.llm.schemas import ChatCompletionRequest, ChatCompletionResponse
from app.llm.exceptions import (
    LLMException,
    LLMAuthenticationException,
    LLMRateLimitException,
    LLMTimeoutException,
    LLMProviderUnavailableException,
    LLMUnsupportedModelException,
    LLMInvalidRequestException
)

def translate_exceptions(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except openai.AuthenticationError as e:
            raise LLMAuthenticationException("OpenAI API key is invalid or unauthorized.", e) from e
        except openai.RateLimitError as e:
            raise LLMRateLimitException("OpenAI rate limit exceeded or quota exhausted.", e) from e
        except openai.APITimeoutError as e:
            raise LLMTimeoutException("OpenAI connection timed out.", e) from e
        except openai.APIConnectionError as e:
            raise LLMProviderUnavailableException("OpenAI API is unreachable or offline.", e) from e
        except openai.NotFoundError as e:
            raise LLMUnsupportedModelException(f"Requested OpenAI model not found: {str(e)}", e) from e
        except openai.BadRequestError as e:
            raise LLMInvalidRequestException(f"Invalid request parameters passed to OpenAI: {str(e)}", e) from e
        except openai.APIError as e:
            raise LLMException(f"OpenAI API error occurred: {str(e)}", e) from e
        except Exception as e:
            raise LLMException(f"Unexpected error in OpenAI provider: {str(e)}", e) from e
    return wrapper

def translate_exceptions_stream(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            async for chunk in func(*args, **kwargs):
                yield chunk
        except openai.AuthenticationError as e:
            raise LLMAuthenticationException("OpenAI API key is invalid or unauthorized.", e) from e
        except openai.RateLimitError as e:
            raise LLMRateLimitException("OpenAI rate limit exceeded or quota exhausted.", e) from e
        except openai.APITimeoutError as e:
            raise LLMTimeoutException("OpenAI connection timed out.", e) from e
        except openai.APIConnectionError as e:
            raise LLMProviderUnavailableException("OpenAI API is unreachable or offline.", e) from e
        except openai.NotFoundError as e:
            raise LLMUnsupportedModelException(f"Requested OpenAI model not found: {str(e)}", e) from e
        except openai.BadRequestError as e:
            raise LLMInvalidRequestException(f"Invalid request parameters passed to OpenAI: {str(e)}", e) from e
        except openai.APIError as e:
            raise LLMException(f"OpenAI API error occurred: {str(e)}", e) from e
        except Exception as e:
            raise LLMException(f"Unexpected error in OpenAI provider: {str(e)}", e) from e
    return wrapper

class OpenAIProvider(BaseLLMProvider):
    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo"
    ]

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None

    def list_models(self) -> List[str]:
        return self.SUPPORTED_MODELS

    @translate_exceptions
    async def health_check(self) -> bool:
        if not self.api_key or not self.client:
            return False

        # Run query with max_tokens=1 for fast validation
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1
        )
        return response is not None

    @translate_exceptions
    async def generate(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if not self.client:
            raise LLMAuthenticationException("OpenAI provider API key is not configured.")
        if request.model not in self.SUPPORTED_MODELS:
            raise LLMUnsupportedModelException(f"Model '{request.model}' is not supported by OpenAI.")

        # Map chat history
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Map config
        kwargs: Dict[str, Any] = {
            "model": request.model,
            "messages": messages
        }
        if request.config:
            if request.config.temperature is not None:
                kwargs["temperature"] = request.config.temperature
            if request.config.top_p is not None:
                kwargs["top_p"] = request.config.top_p
            if request.config.max_tokens is not None:
                kwargs["max_tokens"] = request.config.max_tokens

        response = await self.client.chat.completions.create(**kwargs)
        
        usage_dict = None
        if response.usage:
            usage_dict = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }

        return ChatCompletionResponse(
            content=response.choices[0].message.content or "",
            model=request.model,
            usage=usage_dict
        )

    @translate_exceptions_stream
    async def generate_stream(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        if not self.client:
            raise LLMAuthenticationException("OpenAI provider API key is not configured.")
        if request.model not in self.SUPPORTED_MODELS:
            raise LLMUnsupportedModelException(f"Model '{request.model}' is not supported by OpenAI.")

        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        kwargs: Dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "stream": True
        }
        if request.config:
            if request.config.temperature is not None:
                kwargs["temperature"] = request.config.temperature
            if request.config.top_p is not None:
                kwargs["top_p"] = request.config.top_p
            if request.config.max_tokens is not None:
                kwargs["max_tokens"] = request.config.max_tokens

        response = await self.client.chat.completions.create(**kwargs)
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
