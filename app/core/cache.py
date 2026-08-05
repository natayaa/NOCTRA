# app/core/cache.py
import json
import pickle
import hashlib
import asyncio

from typing import Any, Optional, Union, List, Dict
from functools import wraps
from datetime import datetime, timedelta

from contextlib import asynccontextmanager

try:
    import redis.asyncio as redis
    from redis.asyncio import Redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    Redis = None

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

# ==================== CACHE TTL CONSTANTS ====================

class CacheTTL:
    """Cache TTL constants in seconds"""
    SHORT = 60          # 1 minute
    MEDIUM = 300        # 5 minutes
    LONG = 3600         # 1 hour
    VERY_LONG = 86400   # 24 hours
    FOREVER = 31536000  # 1 year

# ==================== CACHE MANAGER ====================

class CacheManager:
    """Redis cache manager with async support"""
    
    _instance = None
    _redis_client: Optional[Any] = None
    _is_connected = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
        return cls._instance
    
    async def initialize(self):
        """Initialize Redis connection"""
        if not REDIS_AVAILABLE:
            logger.warning("Redis package not installed. Cache will be disabled.")
            return
        
        if self._redis_client is not None:
            return
        
        try:
            self._redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=False,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT
            )
            
            # Test connection
            await self._redis_client.ping()
            self._is_connected = True
            logger.info(f"Redis connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            
        except Exception as e:
            self._is_connected = False
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self._redis_client = None
    
    async def close(self):
        """Close Redis connection"""
        if self._redis_client:
            await self._redis_client.close()
            self._is_connected = False
            logger.info("Redis connection closed")
    
    def is_available(self) -> bool:
        """Check if Redis is available"""
        return self._is_connected and self._redis_client is not None
    
    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage"""
        if isinstance(value, (str, int, float, bool)):
            return str(value).encode('utf-8')
        elif isinstance(value, (dict, list)):
            return json.dumps(value, default=str).encode('utf-8')
        else:
            return pickle.dumps(value)
    
    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage"""
        if data is None:
            return None
        
        # Try JSON first
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        
        # Try pickle
        try:
            return pickle.loads(data)
        except (pickle.PickleError, UnicodeDecodeError):
            pass
        
        # Return as string
        try:
            return data.decode('utf-8')
        except UnicodeDecodeError:
            return data
    
    def _generate_key(self, key: str, prefix: Optional[str] = None) -> str:
        """Generate cache key with prefix"""
        if prefix:
            key = f"{prefix}:{key}"
        return key
    
    async def get(self, key: str, prefix: Optional[str] = None) -> Optional[Any]:
        """Get value from cache"""
        if not self.is_available():
            return None
        
        try:
            key = self._generate_key(key, prefix)
            data = await self._redis_client.get(key)
            if data:
                return self._deserialize(data)
            return None
        except Exception as e:
            logger.error(f"Redis get error for key {key}: {str(e)}")
            return None
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None, prefix: Optional[str] = None, nx: bool = False, xx: bool = False) -> bool:
        """Set value in cache with optional TTL"""
        if not self.is_available():
            return False
        
        try:
            key = self._generate_key(key, prefix)
            serialized = self._serialize(value)
            
            if ttl is None:
                ttl = settings.CACHE_DEFAULT_TTL
            
            if nx:
                return await self._redis_client.setnx(key, serialized)
            elif xx:
                return await self._redis_client.setex(key, ttl, serialized, xx=True)
            else:
                return await self._redis_client.setex(key, ttl, serialized)
        except Exception as e:
            logger.error(f"Redis set error for key {key}: {str(e)}")
            return False
    
    async def delete(self, key: str, prefix: Optional[str] = None) -> int:
        """Delete value from cache"""
        if not self.is_available():
            return 0
        
        try:
            key = self._generate_key(key, prefix)
            return await self._redis_client.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {str(e)}")
            return 0
    
    async def delete_pattern(self, pattern: str, prefix: Optional[str] = None) -> int:
        """Delete all keys matching pattern"""
        if not self.is_available():
            return 0
        
        try:
            pattern = self._generate_key(pattern, prefix)
            keys = await self._redis_client.keys(pattern)
            if keys:
                return await self._redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Redis delete pattern error for {pattern}: {str(e)}")
            return 0
    
    async def exists(self, key: str, prefix: Optional[str] = None) -> bool:
        """Check if key exists in cache"""
        if not self.is_available():
            return False
        
        try:
            key = self._generate_key(key, prefix)
            return await self._redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error for key {key}: {str(e)}")
            return False
    
    async def expire(self, key: str, ttl: int, prefix: Optional[str] = None) -> bool:
        """Set expiration on existing key"""
        if not self.is_available():
            return False
        
        try:
            key = self._generate_key(key, prefix)
            return await self._redis_client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis expire error for key {key}: {str(e)}")
            return False
    
    async def increment(self, key: str, amount: int = 1, prefix: Optional[str] = None) -> int:
        """Increment a counter"""
        if not self.is_available():
            return 0
        
        try:
            key = self._generate_key(key, prefix)
            return await self._redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis increment error for key {key}: {str(e)}")
            return 0
    
    async def hset(self, key: str, field: str, value: Any, prefix: Optional[str] = None) -> int:
        """Set hash field"""
        if not self.is_available():
            return 0
        
        try:
            key = self._generate_key(key, prefix)
            serialized = self._serialize(value)
            return await self._redis_client.hset(key, field, serialized)
        except Exception as e:
            logger.error(f"Redis hset error for key {key}: {str(e)}")
            return 0
    
    async def hget(self, key: str, field: str, prefix: Optional[str] = None) -> Optional[Any]:
        """Get hash field"""
        if not self.is_available():
            return None
        
        try:
            key = self._generate_key(key, prefix)
            data = await self._redis_client.hget(key, field)
            if data:
                return self._deserialize(data)
            return None
        except Exception as e:
            logger.error(f"Redis hget error for key {key}: {str(e)}")
            return None
    
    async def hgetall(self, key: str, prefix: Optional[str] = None) -> Dict[str, Any]:
        """Get all hash fields"""
        if not self.is_available():
            return {}
        
        try:
            key = self._generate_key(key, prefix)
            data = await self._redis_client.hgetall(key)
            if data:
                result = {}
                for field, value in data.items():
                    result[field.decode('utf-8')] = self._deserialize(value)
                return result
            return {}
        except Exception as e:
            logger.error(f"Redis hgetall error for key {key}: {str(e)}")
            return {}
    
    async def pipeline(self):
        """Get Redis pipeline for batch operations"""
        if not self.is_available():
            return None
        
        return self._redis_client.pipeline()

# ==================== CACHE DECORATORS ====================

def cached(key_prefix: str, ttl: int = CacheTTL.MEDIUM, key_builder: Optional[callable] = None, cache_none: bool = False, cache_exceptions: bool = False):
    """
    Cache decorator for functions
    
    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        key_builder: Custom key builder function
        cache_none: Whether to cache None results
        cache_exceptions: Whether to cache exceptions
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            cache = CacheManager()
            
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key builder
                key_parts = [func.__module__, func.__name__]
                
                # Add positional args
                for arg in args:
                    key_parts.append(str(arg))
                
                # Add keyword args (sorted for consistency)
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}={v}")
                
                cache_key = hashlib.md5(
                    ":".join(key_parts).encode('utf-8')
                ).hexdigest()
            
            # Try to get from cache
            if cache.is_available():
                cached_result = await cache.get(cache_key, key_prefix)
                if cached_result is not None:
                    logger.debug(f"Cache hit: {key_prefix}:{cache_key}")
                    return cached_result
            
            # Execute function
            try:
                result = await func(*args, **kwargs)
                
                # Cache result
                if cache_none or result is not None:
                    if cache.is_available():
                        await cache.set(cache_key, result, ttl, key_prefix)
                        logger.debug(f"Cached: {key_prefix}:{cache_key}")
                
                return result
                
            except Exception as e:
                # Cache exceptions if enabled
                if cache_exceptions and cache.is_available():
                    await cache.set(
                        cache_key,
                        {"__exception__": str(e), "__type__": type(e).__name__},
                        ttl,
                        key_prefix
                    )
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Similar logic for sync functions
            cache = CacheManager()
            
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                key_parts = [func.__module__, func.__name__]
                for arg in args:
                    key_parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}={v}")
                cache_key = hashlib.md5(
                    ":".join(key_parts).encode('utf-8')
                ).hexdigest()
            
            if cache.is_available():
                # Run async get in sync context
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                
                cached_result = loop.run_until_complete(cache.get(cache_key, key_prefix))
                if cached_result is not None:
                    logger.debug(f"Cache hit: {key_prefix}:{cache_key}")
                    return cached_result
            
            try:
                result = func(*args, **kwargs)
                if cache_none or result is not None:
                    if cache.is_available():
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        loop.run_until_complete(cache.set(cache_key, result, ttl, key_prefix))
                        logger.debug(f"Cached: {key_prefix}:{cache_key}")
                return result
            except Exception as e:
                if cache_exceptions and cache.is_available():
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    loop.run_until_complete(cache.set(
                        cache_key,
                        {"__exception__": str(e), "__type__": type(e).__name__},
                        ttl,
                        key_prefix
                    ))
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

def invalidate_cache(key_pattern: str, key_prefix: str):
    """Decorator to invalidate cache after function execution"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            cache = CacheManager()
            if cache.is_available():
                await cache.delete_pattern(key_pattern, key_prefix)
                logger.debug(f"Invalidated cache: {key_prefix}:{key_pattern}")
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            cache = CacheManager()
            if cache.is_available():
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(cache.delete_pattern(key_pattern, key_prefix))
                logger.debug(f"Invalidated cache: {key_prefix}:{key_pattern}")
            return result
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator

# ==================== SINGLETON INSTANCE ====================

cache_manager = CacheManager()

async def get_cache() -> CacheManager:
    """Get cache manager instance"""
    return cache_manager

# ==================== EXPORTS ====================

__all__ = [
    'cache_manager',
    'get_cache',
    'cached',
    'invalidate_cache',
    'CacheTTL'
]