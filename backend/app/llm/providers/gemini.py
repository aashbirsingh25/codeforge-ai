import functools
from typing import AsyncGenerator, List, Any
import google.generativeai as genai
from google.api_core.exceptions import (
    InvalidArgument,
    PermissionDenied,
    Unauthenticated,
    ResourceExhausted,
    DeadlineExceeded,
    ServiceUnavailable,
    GoogleAPICallError
)

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
        except (PermissionDenied, Unauthenticated) as e:
            raise LLMAuthenticationException("Gemini API key is invalid or unauthenticated.", e) from e
        except ResourceExhausted as e:
            raise LLMRateLimitException("Gemini rate limit exceeded or quota exhausted.", e) from e
        except DeadlineExceeded as e:
            raise LLMTimeoutException("Gemini connection timed out.", e) from e
        except ServiceUnavailable as e:
            raise LLMProviderUnavailableException("Gemini API service is currently offline or unreachable.", e) from e
        except InvalidArgument as e:
            msg = str(e)
            if "model" in msg.lower() or "not found" in msg.lower():
                raise LLMUnsupportedModelException(f"Requested Gemini model not supported: {msg}", e) from e
            raise LLMInvalidRequestException(f"Invalid request parameters passed to Gemini: {msg}", e) from e
        except GoogleAPICallError as e:
            raise LLMException(f"Google Generative API call failed: {str(e)}", e) from e
        except Exception as e:
            raise LLMException(f"Unexpected error in Gemini provider: {str(e)}", e) from e
    return wrapper

def translate_exceptions_stream(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            async for chunk in func(*args, **kwargs):
                yield chunk
        except (PermissionDenied, Unauthenticated) as e:
            raise LLMAuthenticationException("Gemini API key is invalid or unauthenticated.", e) from e
        except ResourceExhausted as e:
            raise LLMRateLimitException("Gemini rate limit exceeded or quota exhausted.", e) from e
        except DeadlineExceeded as e:
            raise LLMTimeoutException("Gemini connection timed out.", e) from e
        except ServiceUnavailable as e:
            raise LLMProviderUnavailableException("Gemini API service is currently offline or unreachable.", e) from e
        except InvalidArgument as e:
            msg = str(e)
            if "model" in msg.lower() or "not found" in msg.lower():
                raise LLMUnsupportedModelException(f"Requested Gemini model not supported: {msg}", e) from e
            raise LLMInvalidRequestException(f"Invalid request parameters passed to Gemini: {msg}", e) from e
        except GoogleAPICallError as e:
            raise LLMException(f"Google Generative API call failed: {str(e)}", e) from e
        except Exception as e:
            raise LLMException(f"Unexpected error in Gemini provider: {str(e)}", e) from e
    return wrapper

class GeminiProvider(BaseLLMProvider):
    SUPPORTED_MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro"
    ]

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key
        if self.api_key:
            genai.configure(api_key=self.api_key)

    def list_models(self) -> List[str]:
        return self.SUPPORTED_MODELS

    @translate_exceptions
    async def health_check(self) -> bool:
        if not self.api_key:
            return False
        
        # Query smallest model to execute health check quickly
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = await model.generate_content_async(
            "ping",
            generation_config={"max_output_tokens": 1}
        )
        # Verify text was received
        return response is not None

    @translate_exceptions
    async def generate(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        if request.model not in self.SUPPORTED_MODELS:
            raise LLMUnsupportedModelException(f"Model '{request.model}' is not supported by Gemini.")

        # Extract system prompt
        system_instruction = None
        system_msgs = [m for m in request.messages if m.role == "system"]
        if system_msgs:
            system_instruction = system_msgs[-1].content

        # Map chat history
        contents = []
        for msg in request.messages:
            if msg.role == "system":
                continue
            role = "user" if msg.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [msg.content]
            })

        # Map generation config
        generation_config = {}
        if request.config:
            if request.config.temperature is not None:
                generation_config["temperature"] = request.config.temperature
            if request.config.top_p is not None:
                generation_config["top_p"] = request.config.top_p
            if request.config.max_tokens is not None:
                generation_config["max_output_tokens"] = request.config.max_tokens

        model = genai.GenerativeModel(
            model_name=request.model,
            system_instruction=system_instruction
        )

        response = await model.generate_content_async(
            contents,
            generation_config=generation_config
        )

        return ChatCompletionResponse(
            content=response.text,
            model=request.model
        )

    @translate_exceptions_stream
    async def generate_stream(self, request: ChatCompletionRequest) -> AsyncGenerator[str, None]:
        if request.model not in self.SUPPORTED_MODELS:
            raise LLMUnsupportedModelException(f"Model '{request.model}' is not supported by Gemini.")

        # Extract system prompt
        system_instruction = None
        system_msgs = [m for m in request.messages if m.role == "system"]
        if system_msgs:
            system_instruction = system_msgs[-1].content

        contents = []
        for msg in request.messages:
            if msg.role == "system":
                continue
            role = "user" if msg.role == "user" else "model"
            contents.append({
                "role": role,
                "parts": [msg.content]
            })

        generation_config = {}
        if request.config:
            if request.config.temperature is not None:
                generation_config["temperature"] = request.config.temperature
            if request.config.top_p is not None:
                generation_config["top_p"] = request.config.top_p
            if request.config.max_tokens is not None:
                generation_config["max_output_tokens"] = request.config.max_tokens

        model = genai.GenerativeModel(
            model_name=request.model,
            system_instruction=system_instruction
        )

        response = await model.generate_content_async(
            contents,
            generation_config=generation_config,
            stream=True
        )

        async for chunk in response:
            if chunk.text:
                yield chunk.text
