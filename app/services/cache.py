import json
from app.core.config import settings
import time
from functools import lru_cache, wraps
from typing import Any, Callable, Optional

try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:  # pragma: no cover
    aioredis = None


class Cache:
    def __init__(self, ttl_seconds: int = 86400, maxsize: int = 256):
        self.ttl = ttl_seconds
        self._redis = None
        self._lru_store: dict[str, tuple[float, Any]] = {}
        self._lru_maxsize = maxsize
        url = settings.REDIS_HOST
        if aioredis and url:
            try:
                host = settings.REDIS_HOST or "localhost"
                port = int(settings.REDIS_PORT or 6379)
                db = int(settings.REDIS_DB or 0)
                self._redis = aioredis.Redis(host=host, port=port, db=db, decode_responses=True, socket_timeout=1.0, socket_connect_timeout=1.0)
            except Exception:
                self._redis = None
        from app.core.logging import logger
        if self._redis:
            logger.info("Redis cache enabled")
        else:
            logger.info("Redis cache disabled; using in-memory LRU cache")

    def is_redis(self) -> bool:
        return self._redis is not None

    async def aget(self, key: str) -> Optional[Any]:
        if self._redis:
            try:
                v = await self._redis.get(key)
                if v is None:
                    return None
                return json.loads(v)
            except Exception:
                return None
        now = time.time()
        item = self._lru_store.get(key)
        if not item:
            return None
        exp, val = item
        if now > exp:
            self._lru_store.pop(key, None)
            return None
        return val

    async def aset(self, key: str, value: Any) -> None:
        if self._redis:
            try:
                await self._redis.setex(key, self.ttl, json.dumps(value))
                return
            except Exception:
                pass
        now = time.time()
        self._lru_store[key] = (now + self.ttl, value)
        if len(self._lru_store) > self._lru_maxsize:
            self._lru_store.pop(next(iter(self._lru_store)))

CACHE_INSTANCE = Cache(ttl_seconds=86400)

def make_timed_lru(seconds: int, maxsize: int = 128):
    def wrapper(func: Callable):
        cached = lru_cache(maxsize=maxsize)(func)
        cached.lifetime = seconds
        cached.expiration = time.time() + seconds

        @wraps(cached)
        def wrapped(*args, **kwargs):
            if time.time() > cached.expiration:
                cached.cache_clear()
                cached.expiration = time.time() + cached.lifetime
            return cached(*args, **kwargs)

        return wrapped

    return wrapper
