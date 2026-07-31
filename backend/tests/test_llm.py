import pytest
import os
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch
from typing import AsyncGenerator

from app.llm.factory import ProviderFactory
from app.llm.providers.gemini import GeminiProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.base import BaseLLMProvider
from app.llm.schemas import ChatCompletionRequest, ChatCompletionResponse, ChatMessage, GenerationConfig
from app.llm.exceptions import (
    LLMException,
    LLMAuthenticationException,
    LLMRateLimitException,
    LLMTimeoutException,
    LLMProviderUnavailableException,
    LLMUnsupportedModelException,
    LLMInvalidRequestException
)

# Helper to mock async iterators in streaming tests
class AsyncIteratorMock:
    def __init__(self, items):
        self.items = items
        self.idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.idx < len(self.items):
            item = self.items[self.idx]
            self.idx += 1
            return item
        else:
            raise StopAsyncIteration

# ==========================================
# 1. ProviderFactory Tests
# ==========================================

def test_provider_factory_resolution():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_gemini", "OPENAI_API_KEY": "test_openai"}):
        gemini_prov = ProviderFactory.get_provider("gemini")
        assert isinstance(gemini_prov, GeminiProvider)
        assert gemini_prov.api_key == "test_gemini"

        openai_prov = ProviderFactory.get_provider("openai")
        assert isinstance(openai_prov, OpenAIProvider)
        assert openai_prov.api_key == "test_openai"

def test_provider_factory_case_insensitive():
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test"}):
        prov = ProviderFactory.get_provider("  GeMiNi  ")
        assert isinstance(prov, GeminiProvider)

def test_provider_factory_unsupported():
    with pytest.raises(ValueError) as excinfo:
        ProviderFactory.get_provider("unknown_provider")
    assert "unsupported LLM provider" in str(excinfo.value)


# ==========================================
# 2. Exception Handling Translator Tests
# ==========================================

@pytest.mark.asyncio
async def test_gemini_exception_translation():
    from google.api_core.exceptions import PermissionDenied, ResourceExhausted, DeadlineExceeded
    provider = GeminiProvider(api_key="test_key")
    req = ChatCompletionRequest(
        model="gemini-1.5-flash",
        messages=[ChatMessage(role="user", content="hello")]
    )

    with patch("google.generativeai.GenerativeModel.generate_content_async") as mock_gen:
        # Test PermissionDenied
        mock_gen.side_effect = PermissionDenied("auth failed")
        with pytest.raises(LLMAuthenticationException):
            await provider.generate(req)

        # Test ResourceExhausted
        mock_gen.side_effect = ResourceExhausted("limit exceeded")
        with pytest.raises(LLMRateLimitException):
            await provider.generate(req)

        # Test DeadlineExceeded
        mock_gen.side_effect = DeadlineExceeded("timed out")
        with pytest.raises(LLMTimeoutException):
            await provider.generate(req)

@pytest.mark.asyncio
async def test_openai_exception_translation():
    import openai
    provider = OpenAIProvider(api_key="test_key")
    req = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[ChatMessage(role="user", content="hello")]
    )

    # We must patch mock_client.chat.completions.create
    with patch.object(provider.client.chat.completions, "create") as mock_create:
        # Test AuthenticationError
        mock_create.side_effect = openai.AuthenticationError(
            message="auth failed",
            response=MagicMock(),
            body=None
        )
        with pytest.raises(LLMAuthenticationException):
            await provider.generate(req)

        # Test RateLimitError
        mock_create.side_effect = openai.RateLimitError(
            message="limits hit",
            response=MagicMock(),
            body=None
        )
        with pytest.raises(LLMRateLimitException):
            await provider.generate(req)


# ==========================================
# 3. Gemini Generation Tests
# ==========================================

@pytest.mark.asyncio
async def test_gemini_generate_static():
    provider = GeminiProvider(api_key="test_key")
    req = ChatCompletionRequest(
        model="gemini-1.5-flash",
        messages=[
            ChatMessage(role="system", content="you are an assistant"),
            ChatMessage(role="user", content="ping")
        ],
        config=GenerationConfig(temperature=0.5, top_p=0.9, max_tokens=10)
    )

    mock_response = AsyncMock()
    mock_response.text = "pong response"

    with patch("google.generativeai.GenerativeModel.generate_content_async", return_value=mock_response) as mock_gen:
        res = await provider.generate(req)
        assert res.content == "pong response"
        assert res.model == "gemini-1.5-flash"
        
        # Verify the structure passed to generate_content_async
        mock_gen.assert_called_once()
        args, kwargs = mock_gen.call_args
        assert args[0] == [{"role": "user", "parts": ["ping"]}]
        assert kwargs["generation_config"] == {"temperature": 0.5, "top_p": 0.9, "max_output_tokens": 10}

@pytest.mark.asyncio
async def test_gemini_generate_stream():
    provider = GeminiProvider(api_key="test_key")
    req = ChatCompletionRequest(
        model="gemini-1.5-flash",
        messages=[ChatMessage(role="user", content="hello")]
    )

    # Mock chunk objects returned by Gemini stream async generator
    chunk1 = MagicMock()
    chunk1.text = "Hello "
    chunk2 = MagicMock()
    chunk2.text = "world!"
    
    mock_stream = AsyncIteratorMock([chunk1, chunk2])

    with patch("google.generativeai.GenerativeModel.generate_content_async", return_value=mock_stream) as mock_gen:
        stream = provider.generate_stream(req)
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        assert chunks == ["Hello ", "world!"]
        mock_gen.assert_called_once_with([{"role": "user", "parts": ["hello"]}], generation_config={}, stream=True)


# ==========================================
# 4. OpenAI Generation Tests
# ==========================================

@pytest.mark.asyncio
async def test_openai_generate_static():
    provider = OpenAIProvider(api_key="test_key")
    req = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[ChatMessage(role="user", content="hello")],
        config=GenerationConfig(temperature=0.7)
    )

    # Mock response structure of openai client
    mock_choice = MagicMock()
    mock_choice.message.content = "openai response content"
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=10, total_tokens=15)

    with patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_response
        res = await provider.generate(req)
        
        assert res.content == "openai response content"
        assert res.usage["total_tokens"] == 15
        mock_create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.7
        )

@pytest.mark.asyncio
async def test_openai_generate_stream():
    provider = OpenAIProvider(api_key="test_key")
    req = ChatCompletionRequest(
        model="gpt-3.5-turbo",
        messages=[ChatMessage(role="user", content="stream test")]
    )

    # Mock chunks yielded by OpenAI streaming client
    chunk1 = MagicMock()
    chunk1.choices = [MagicMock(delta=MagicMock(content="yield "))]
    chunk2 = MagicMock()
    chunk2.choices = [MagicMock(delta=MagicMock(content="chunk"))]
    
    mock_stream = AsyncIteratorMock([chunk1, chunk2])

    with patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_stream
        stream = provider.generate_stream(req)
        chunks = []
        async for chunk in stream:
            chunks.append(chunk)

        assert chunks == ["yield ", "chunk"]
        mock_create.assert_called_once_with(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "stream test"}],
            stream=True
        )


@pytest.mark.asyncio
async def test_gemini_health_check_validation_success():
    provider = GeminiProvider(api_key="test_key")
    
    mock_model1 = MagicMock()
    mock_model1.name = "models/gemini-2.5-pro"
    
    with patch("google.generativeai.list_models", return_value=[mock_model1]), \
         patch("google.generativeai.GenerativeModel.generate_content_async", new_callable=AsyncMock) as mock_gen, \
         patch.dict(os.environ, {"GEMINI_MODEL": "gemini-2.5-pro"}):
        
        mock_gen.return_value = MagicMock()
        result = await provider.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_gemini_health_check_validation_failure():
    provider = GeminiProvider(api_key="test_key")
    
    mock_model1 = MagicMock()
    mock_model1.name = "models/gemini-2.5-flash"
    
    with patch("google.generativeai.list_models", return_value=[mock_model1]), \
         patch.dict(os.environ, {"GEMINI_MODEL": "gemini-2.5-pro"}):
        
        with pytest.raises(LLMUnsupportedModelException) as excinfo:
            await provider.health_check()
        assert "is not found or unsupported by the current API/SDK version" in str(excinfo.value)
        assert "gemini-2.5-flash" in str(excinfo.value)


@pytest.mark.asyncio
async def test_openai_health_check_validation_success():
    provider = OpenAIProvider(api_key="test_key")
    
    mock_model1 = MagicMock()
    mock_model1.id = "gpt-4o"
    mock_models_list = MagicMock()
    mock_models_list.data = [mock_model1]
    
    with patch.object(provider.client.models, "list", new_callable=AsyncMock) as mock_list, \
         patch.object(provider.client.chat.completions, "create", new_callable=AsyncMock) as mock_create, \
         patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4o"}):
        
        mock_list.return_value = mock_models_list
        mock_create.return_value = MagicMock()
        
        result = await provider.health_check()
        assert result is True


@pytest.mark.asyncio
async def test_openai_health_check_validation_failure():
    provider = OpenAIProvider(api_key="test_key")
    
    mock_model1 = MagicMock()
    mock_model1.id = "gpt-3.5-turbo"
    mock_models_list = MagicMock()
    mock_models_list.data = [mock_model1]
    
    with patch.object(provider.client.models, "list", new_callable=AsyncMock) as mock_list, \
         patch.dict(os.environ, {"OPENAI_MODEL": "gpt-4o"}):
        
        mock_list.return_value = mock_models_list
        
        with pytest.raises(LLMUnsupportedModelException) as excinfo:
            await provider.health_check()
        assert "is not found or unsupported" in str(excinfo.value)
        assert "gpt-3.5-turbo" in str(excinfo.value)


# ==========================================
# 5. Redis LLM Caching Tests
# ==========================================

class FakeRedisClient:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def set(self, key, val, ex=None):
        self.store[key] = val


@pytest.mark.asyncio
async def test_llm_cache_hit_temperature_zero():
    fake_redis = FakeRedisClient()
    from app.llm.cache import llm_cache
    with patch.object(llm_cache, "get_client", return_value=fake_redis):
        provider = GeminiProvider(api_key="test_key")
        req = ChatCompletionRequest(
            model="gemini-1.5-flash",
            messages=[ChatMessage(role="user", content="deterministic prompt")],
            config=GenerationConfig(temperature=0.0)
        )
        
        mock_response = ChatCompletionResponse(content="cached answer", model="gemini-1.5-flash")
        
        with patch.object(provider, "_generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            # First call: cache miss -> calls provider _generate
            res1 = await provider.generate(req)
            assert res1.content == "cached answer"
            assert mock_gen.call_count == 1
            
            # Second call with identical input and temp=0: cache hit -> returns without calling provider _generate
            res2 = await provider.generate(req)
            assert res2.content == "cached answer"
            assert mock_gen.call_count == 1  # Provider NOT invoked again!


@pytest.mark.asyncio
async def test_llm_cache_bypassed_for_non_zero_temperature():
    fake_redis = FakeRedisClient()
    from app.llm.cache import llm_cache
    with patch.object(llm_cache, "get_client", return_value=fake_redis):
        provider = GeminiProvider(api_key="test_key")
        
        # 1. Non-zero temperature (0.7)
        req_temp = ChatCompletionRequest(
            model="gemini-1.5-flash",
            messages=[ChatMessage(role="user", content="sampling prompt")],
            config=GenerationConfig(temperature=0.7)
        )
        mock_response = ChatCompletionResponse(content="sampled answer", model="gemini-1.5-flash")
        
        with patch.object(provider, "_generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            await provider.generate(req_temp)
            await provider.generate(req_temp)
            # Both calls must invoke _generate (no caching when temperature > 0)
            assert mock_gen.call_count == 2

        # 2. Temperature is None
        req_none = ChatCompletionRequest(
            model="gemini-1.5-flash",
            messages=[ChatMessage(role="user", content="default prompt")]
        )
        with patch.object(provider, "_generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            await provider.generate(req_none)
            await provider.generate(req_none)
            # Both calls must invoke _generate (no caching when temperature is None)
            assert mock_gen.call_count == 2


@pytest.mark.asyncio
async def test_llm_cache_redis_unreachable_fallback():
    from app.llm.cache import llm_cache
    
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(side_effect=Exception("Redis connection error"))
    mock_redis.set = AsyncMock(side_effect=Exception("Redis connection error"))
    
    with patch.object(llm_cache, "get_client", return_value=mock_redis):
        provider = GeminiProvider(api_key="test_key")
        req = ChatCompletionRequest(
            model="gemini-1.5-flash",
            messages=[ChatMessage(role="user", content="fallback test")],
            config=GenerationConfig(temperature=0.0)
        )
        mock_response = ChatCompletionResponse(content="fallback answer", model="gemini-1.5-flash")
        
        with patch.object(provider, "_generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = mock_response
            
            # Request should succeed cleanly via provider call despite Redis failure
            res = await provider.generate(req)
            assert res.content == "fallback answer"
            assert mock_gen.call_count == 1

