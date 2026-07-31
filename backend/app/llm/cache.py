import hashlib
import json
import logging
from typing import Optional
import redis.asyncio as redis

from app.llm.schemas import ChatCompletionRequest, ChatCompletionResponse

logger = logging.getLogger("app.llm.cache")


class LLMCache:
    """Redis-backed cache for deterministic LLM completion requests (temperature == 0)."""

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url
        self._client: Optional[redis.Redis] = None

    @property
    def redis_url(self) -> str:
        if self._redis_url:
            return self._redis_url
        from app.core.config import settings
        return str(settings.REDIS_URL)

    def get_client(self) -> redis.Redis:
        if self._client is None:
            self._client = redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def _compute_key(self, request: ChatCompletionRequest) -> str:
        """Computes SHA-256 hash key of the full serialized ChatCompletionRequest."""
        raw_bytes = request.model_dump_json().encode("utf-8")
        sha256_hash = hashlib.sha256(raw_bytes).hexdigest()
        return f"llm_cache:{sha256_hash}"

    async def get(self, request: ChatCompletionRequest) -> Optional[ChatCompletionResponse]:
        """Retrieves cached response if temperature is explicitly 0."""
        # Only cache when request.config exists and temperature is explicitly 0
        if (
            not request.config
            or request.config.temperature is None
            or request.config.temperature != 0
            or isinstance(request.config.temperature, bool)
        ):
            return None

        try:
            key = self._compute_key(request)
            client = self.get_client()
            cached_val = await client.get(key)
            if cached_val:
                logger.info(f"LLM Cache Hit for key {key[:18]}...")
                data = json.loads(cached_val)
                return ChatCompletionResponse(**data)
        except Exception as e:
            logger.warning(f"Redis cache lookup failed (falling through to LLM call): {e}")

        return None

    async def set(
        self,
        request: ChatCompletionRequest,
        response: ChatCompletionResponse,
        ttl: int = 3600
    ) -> None:
        """Stores ChatCompletionResponse in Redis with 1-hour TTL if temperature is explicitly 0."""
        if (
            not request.config
            or request.config.temperature is None
            or request.config.temperature != 0
            or isinstance(request.config.temperature, bool)
        ):
            return

        try:
            key = self._compute_key(request)
            client = self.get_client()
            val_json = response.model_dump_json()
            await client.set(key, val_json, ex=ttl)
            logger.info(f"Cached LLM response under key {key[:18]}... (TTL: {ttl}s)")
        except Exception as e:
            logger.warning(f"Redis cache store failed: {e}")

    async def close(self):
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None


llm_cache = LLMCache()
