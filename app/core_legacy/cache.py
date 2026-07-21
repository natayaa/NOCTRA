# core/cache.py
import json
from typing import Optional, Any, Callable
from functools import wraps
import redis.asyncio as redis
from core.config import settings


class Cache:
    """Redis cache wrapper."""

    _client: Optional[redis.Redis] = None

    @classmethod
    async def get_client(cls) -> redis.Redis:
        """Get Redis client."""
        if cls._client is None:
            cls._client = redis.from_url(
                settings.REDIS_URL or "redis://localhost:6379/0",
                decode_responses=True,
            )
        return cls._client

    @classmethod
    async def get(cls, key: str) -> Optional[Any]:
        """Get value from cache."""
        client = await cls.get_client()
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None

    @classmethod
    async def set(
        cls,
        key: str,
        value: Any,
        ttl: int = 300  # 5 minutes
    ) -> bool:
        """Set value in cache."""
        client = await cls.get_client()
        return await client.setex(key, ttl, json.dumps(value))

    @classmethod
    async def delete(cls, key: str) -> bool:
        """Delete from cache."""
        client = await cls.get_client()
        return await client.delete(key) > 0

    @classmethod
    async def clear_pattern(cls, pattern: str) -> int:
        """Clear keys matching pattern."""
        client = await cls.get_client()
        keys = await client.keys(pattern)
        if keys:
            return await client.delete(*keys)
        return 0


# =============================================================================
# Cache Decorator
# =============================================================================

def cached(ttl: int = 300, key_prefix: str = ""):
    """Decorator untuk caching function result."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix or func.__name__]
            key_parts.extend([str(a) for a in args])
            key_parts.extend([f"{k}:{v}" for k, v in kwargs.items()])
            cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_data = await Cache.get(cache_key)
            if cached_data is not None:
                return cached_data

            # Execute function
            result = await func(*args, **kwargs)

            # Cache result
            await Cache.set(cache_key, result, ttl)

            return result
        return wrapper
    return decorator
