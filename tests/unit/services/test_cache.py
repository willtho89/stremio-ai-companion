"""
Tests for the cache service.
"""

import time
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from app.services.cache import Cache, MemoryBackend, RedisBackend, CacheBackend, RedisError

# Import aioredis or create a mock if not available
try:
    import redis.asyncio as aioredis
except ImportError:
    # Create a mock RedisError for testing
    class MockRedisError(Exception):
        pass

    class MockAioRedis:
        RedisError = MockRedisError

    aioredis = MockAioRedis


class TestMemoryBackend:
    """Tests for the MemoryBackend class."""

    @pytest.fixture
    def memory_backend(self):
        """Fixture providing a MemoryBackend instance."""
        return MemoryBackend(maxsize=3)

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, memory_backend):
        """Test getting a nonexistent key returns None."""
        result = await memory_backend.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self, memory_backend):
        """Test setting and getting a value."""
        await memory_backend.set("test_key", "test_value", 60)
        result = await memory_backend.get("test_key")
        assert result == "test_value"

    @pytest.mark.asyncio
    async def test_expired_key(self, memory_backend):
        """Test that expired keys return None."""
        await memory_backend.set("test_key", "test_value", 1)
        # Wait for expiration
        time.sleep(1.1)
        result = await memory_backend.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_lru_eviction(self, memory_backend):
        """Test that least recently used items are evicted when maxsize is reached."""
        # Set maxsize + 1 items
        await memory_backend.set("key1", "value1", 60)
        await memory_backend.set("key2", "value2", 60)
        await memory_backend.set("key3", "value3", 60)
        # Access key1 to make it most recently used
        await memory_backend.get("key1")
        # Add another item, should evict key2 (least recently used)
        await memory_backend.set("key4", "value4", 60)

        # key1 and key3 should still be there
        assert await memory_backend.get("key1") == "value1"
        assert await memory_backend.get("key3") == "value3"
        assert await memory_backend.get("key4") == "value4"
        # key2 should be evicted
        assert await memory_backend.get("key2") is None

    @pytest.mark.asyncio
    async def test_delete(self, memory_backend):
        """Test deleting a key."""
        await memory_backend.set("test_key", "test_value", 60)
        await memory_backend.delete("test_key")
        result = await memory_backend.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear(self, memory_backend):
        """Test clearing all keys."""
        await memory_backend.set("key1", "value1", 60)
        await memory_backend.set("key2", "value2", 60)
        await memory_backend.clear()
        assert await memory_backend.get("key1") is None
        assert await memory_backend.get("key2") is None


class TestRedisBackend:
    """Tests for the RedisBackend class using mocks."""

    @pytest.fixture
    def mock_redis(self):
        """Fixture providing a mocked Redis client."""
        with patch("app.services.cache.aioredis") as mock_aioredis:
            mock_redis = MagicMock()
            # Make Redis methods awaitable
            mock_redis.get = AsyncMock()
            mock_redis.setex = AsyncMock()
            mock_redis.delete = AsyncMock()
            mock_redis.flushdb = AsyncMock()
            mock_redis.aclose = AsyncMock()
            mock_aioredis.Redis.return_value = mock_redis
            yield mock_redis

    @pytest.fixture
    def redis_backend(self, mock_redis):
        """Fixture providing a RedisBackend instance with mocked Redis client."""
        return RedisBackend(host="localhost", port=6379, db=0)

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, redis_backend, mock_redis):
        """Test getting a nonexistent key returns None."""
        mock_redis.get.return_value = None
        result = await redis_backend.get("nonexistent")
        assert result is None
        mock_redis.get.assert_called_once_with("nonexistent")

    @pytest.mark.asyncio
    async def test_get_existing_key(self, redis_backend, mock_redis):
        """Test getting an existing key returns the deserialized value."""
        mock_redis.get.return_value = '{"key": "value"}'
        result = await redis_backend.get("test_key")
        assert result == {"key": "value"}
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_set(self, redis_backend, mock_redis):
        """Test setting a value."""
        await redis_backend.set("test_key", {"key": "value"}, 60)
        mock_redis.setex.assert_called_once()
        # Check that the key and TTL were passed correctly
        args = mock_redis.setex.call_args[0]
        assert args[0] == "test_key"
        assert args[1] == 60
        # The third argument is the serialized value, which is a string
        assert isinstance(args[2], str)

        # Test error handling
        mock_redis.setex.side_effect = RedisError("Redis error")
        # Should not raise exception
        await redis_backend.set("test_key", {"key": "value"}, 60)

    @pytest.mark.asyncio
    async def test_delete(self, redis_backend, mock_redis):
        """Test deleting a key."""
        await redis_backend.delete("test_key")
        mock_redis.delete.assert_called_once_with("test_key")

        # Test error handling
        mock_redis.delete.side_effect = RedisError("Redis error")
        # Should not raise exception
        await redis_backend.delete("test_key")

    @pytest.mark.asyncio
    async def test_clear(self, redis_backend, mock_redis):
        """Test clearing all keys."""
        await redis_backend.clear()
        mock_redis.flushdb.assert_called_once()

        # Test error handling
        mock_redis.flushdb.side_effect = RedisError("Redis error")
        # Should not raise exception
        await redis_backend.clear()

    @pytest.mark.asyncio
    async def test_close(self, redis_backend, mock_redis):
        """Test closing the Redis connection."""
        await redis_backend.close()
        mock_redis.aclose.assert_called_once()

        # Test error handling
        mock_redis.aclose.side_effect = RedisError("Redis error")
        # Should not raise exception
        await redis_backend.close()


class TestCache:
    """Tests for the high-level Cache class."""

    @pytest.fixture
    def mock_settings(self):
        """Fixture providing mocked settings."""
        with patch("app.services.cache.settings") as mock_settings:
            # Default to no Redis
            mock_settings.REDIS_HOST = None
            yield mock_settings

    @pytest.mark.asyncio
    async def test_memory_backend_creation(self, mock_settings):
        """Test that MemoryBackend is created when Redis is not configured."""
        cache = Cache()
        assert isinstance(cache._backend, MemoryBackend)
        assert cache.is_redis is False

    @pytest.mark.asyncio
    async def test_redis_backend_creation(self, mock_settings):
        """Test that RedisBackend is created when Redis is configured."""
        with patch("app.services.cache.RedisBackend") as mock_redis_backend:
            mock_settings.REDIS_HOST = "localhost"
            mock_settings.REDIS_PORT = 6379
            mock_settings.REDIS_DB = 0

            mock_instance = MagicMock()
            mock_redis_backend.return_value = mock_instance

            cache = Cache()
            assert cache._backend == mock_instance
            mock_redis_backend.assert_called_once_with(host="localhost", port=6379, db=0)

    @pytest.mark.asyncio
    async def test_aget(self):
        """Test that aget delegates to backend.get."""
        mock_backend = MagicMock(spec=CacheBackend)
        mock_backend.get.return_value = "test_value"

        cache = Cache()
        cache._backend = mock_backend

        result = await cache.aget("test_key")
        assert result == "test_value"
        mock_backend.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_aset(self):
        """Test that aset delegates to backend.set with correct TTL."""
        mock_backend = MagicMock(spec=CacheBackend)

        cache = Cache(ttl_seconds=120)
        cache._backend = mock_backend

        await cache.aset("test_key", "test_value")
        mock_backend.set.assert_called_once_with("test_key", "test_value", 120)

        # Test with custom TTL
        mock_backend.reset_mock()
        await cache.aset("test_key", "test_value", ttl=60)
        mock_backend.set.assert_called_once_with("test_key", "test_value", 60)

    @pytest.mark.asyncio
    async def test_adelete(self):
        """Test that adelete delegates to backend.delete."""
        mock_backend = MagicMock(spec=CacheBackend)

        cache = Cache()
        cache._backend = mock_backend

        await cache.adelete("test_key")
        mock_backend.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_aclear(self):
        """Test that aclear delegates to backend.clear."""
        mock_backend = MagicMock(spec=CacheBackend)

        cache = Cache()
        cache._backend = mock_backend

        await cache.aclear()
        mock_backend.clear.assert_called_once()

    @pytest.mark.asyncio
    async def test_aclose(self):
        """Test that aclose delegates to backend.close."""
        mock_backend = MagicMock(spec=CacheBackend)

        cache = Cache()
        cache._backend = mock_backend

        await cache.aclose()
        mock_backend.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        """Test that Cache works as an async context manager."""
        mock_backend = MagicMock(spec=CacheBackend)

        cache = Cache()
        cache._backend = mock_backend

        async with cache as c:
            assert c == cache

        mock_backend.close.assert_called_once()
