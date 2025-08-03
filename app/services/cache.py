import json
import time
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Optional, Union
import logging

from app.core.config import settings

try:
    import redis.asyncio as aioredis  # type: ignore
except ImportError:  # pragma: no cover
    aioredis = None

logger = logging.getLogger(__name__)


class CacheBackend(ABC):
    """Abstract base class for cache backends."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int) -> None:
        """Set a value in the cache with TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a key from the cache."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cache entries."""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """Close the cache backend."""
        pass


class RedisBackend(CacheBackend):
    """Redis cache backend."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        if not aioredis:
            raise ImportError("redis package is required for RedisBackend")
        
        self._redis = aioredis.Redis(
            host=host,
            port=port,
            db=db,
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
            retry_on_timeout=True,
            health_check_interval=30
        )
    
    async def get(self, key: str) -> Optional[Any]:
        try:
            value = await self._redis.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (aioredis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Redis get error for key '{key}': {e}")
            return None
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        try:
            serialized = json.dumps(value, default=str)
            await self._redis.setex(key, ttl, serialized)
        except (aioredis.RedisError, TypeError, ValueError) as e:
            logger.warning(f"Redis set error for key '{key}': {e}")
    
    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except aioredis.RedisError as e:
            logger.warning(f"Redis delete error for key '{key}': {e}")
    
    async def clear(self) -> None:
        try:
            await self._redis.flushdb()
        except aioredis.RedisError as e:
            logger.warning(f"Redis clear error: {e}")
    
    async def close(self) -> None:
        try:
            await self._redis.aclose()
        except aioredis.RedisError as e:
            logger.warning(f"Redis close error: {e}")


class MemoryBackend(CacheBackend):
    """In-memory LRU cache backend."""
    
    def __init__(self, maxsize: int = 256):
        self._store: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self._maxsize = maxsize
    
    async def get(self, key: str) -> Optional[Any]:
        if key not in self._store:
            return None
        
        exp_time, value = self._store[key]
        
        if time.time() > exp_time:
            del self._store[key]
            return None
        
        # Move to end (most recently used)
        self._store.move_to_end(key)
        return value
    
    async def set(self, key: str, value: Any, ttl: int) -> None:
        exp_time = time.time() + ttl
        self._store[key] = (exp_time, value)
        self._store.move_to_end(key)
        
        # Remove oldest items if over capacity
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)
    
    async def delete(self, key: str) -> None:
        self._store.pop(key, None)
    
    async def clear(self) -> None:
        self._store.clear()
    
    async def close(self) -> None:
        pass  # No cleanup needed for memory backend


class Cache:
    """High-level cache interface with automatic backend selection."""
    
    def __init__(self, ttl_seconds: int = 86400, maxsize: int = 256):
        self.ttl = ttl_seconds
        self._backend = self._create_backend(maxsize)
    
    def _create_backend(self, maxsize: int) -> CacheBackend:
        """Create appropriate cache backend based on configuration."""
        if aioredis and settings.REDIS_HOST:
            try:
                host = settings.REDIS_HOST
                port = int(settings.REDIS_PORT or 6379)
                db = int(settings.REDIS_DB or 0)
                backend = RedisBackend(host=host, port=port, db=db)
                logger.info("Redis cache backend initialized")
                return backend
            except Exception as e:
                logger.warning(f"Failed to initialize Redis backend: {e}")
        
        logger.info("Using in-memory cache backend")
        return MemoryBackend(maxsize=maxsize)
    
    @property
    def is_redis(self) -> bool:
        """Check if using Redis backend."""
        return isinstance(self._backend, RedisBackend)
    
    async def aget(self, key: str) -> Optional[Any]:
        """Get a value from the cache."""
        return await self._backend.get(key)
    
    async def aset(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache."""
        ttl = ttl or self.ttl
        await self._backend.set(key, value, ttl)
    
    async def adelete(self, key: str) -> None:
        """Delete a key from the cache."""
        await self._backend.delete(key)
    
    async def aclear(self) -> None:
        """Clear all cache entries."""
        await self._backend.clear()
    
    async def aclose(self) -> None:
        """Close the cache and cleanup resources."""
        await self._backend.close()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.aclose()


CACHE_INSTANCE = Cache(ttl_seconds=86400)
