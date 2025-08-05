"""
Tests for the _cached_catalog function in the Stremio API.
"""

from unittest.mock import patch, AsyncMock

import pytest

from app.api.stremio import _cached_catalog
from app.models.config import Config
from app.models.enums import ContentType


@pytest.fixture
def mock_cache():
    """Fixture providing a mocked Cache instance."""
    with patch("app.api.stremio.CACHE_INSTANCE") as mock_cache:
        # Default to non-Redis cache
        mock_cache.is_redis = False
        mock_cache.aget = AsyncMock()
        mock_cache.aset = AsyncMock()
        yield mock_cache


@pytest.fixture
def mock_process_catalog_request():
    """Fixture providing a mocked _process_catalog_request function."""
    with patch("app.api.stremio._process_catalog_request_internal") as mock_fn:
        mock_fn.return_value = {"metas": [{"name": "Test Movie", "id": "test-id"}]}
        yield mock_fn


@pytest.fixture
def mock_encryption_service():
    """Fixture providing a mocked EncryptionService."""
    with patch("app.api.stremio.encryption_service") as mock:
        # Create a valid config for testing
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )
        mock.decrypt.return_value = config.model_dump_json()
        yield mock


@pytest.fixture
def mock_apply_rpdb_posters():
    """Fixture providing a mocked _apply_rpdb_posters function."""
    with patch("app.api.stremio._apply_rpdb_posters") as mock_fn:
        # Return the input metas unchanged
        mock_fn.side_effect = lambda metas, rpdb_service: metas
        yield mock_fn


class TestCachedCatalog:
    """Tests for the _cached_catalog function."""

    @pytest.mark.asyncio
    async def test_lru_cache_skip_zero(
        self, mock_cache, mock_process_catalog_request, mock_encryption_service, mock_apply_rpdb_posters
    ):
        """Test LRU cache behavior with skip=0."""
        # Set up cache miss
        mock_cache.aget.return_value = None

        result = await _cached_catalog("test_config", ContentType.MOVIE, "trending_movie")

        # Verify cache key format
        cache_key_arg = mock_cache.aget.call_args[0][0]
        assert cache_key_arg == "catalog:trending_movie"

        # Verify _process_catalog_request_internal was called with correct args
        mock_process_catalog_request.assert_called_once()
        assert mock_process_catalog_request.call_args[0][0] == "test_config"
        assert "trending" in mock_process_catalog_request.call_args[0][1].lower()
        assert mock_process_catalog_request.call_args[0][2] == ContentType.MOVIE

        # Verify result
        assert result == {"metas": [{"name": "Test Movie", "id": "test-id"}]}

        # Verify cache set
        mock_cache.aset.assert_called_once()
        assert mock_cache.aset.call_args[0][0] == cache_key_arg
        assert mock_cache.aset.call_args[0][1] == result

    @pytest.mark.asyncio
    async def test_lru_cache_hit(
        self, mock_cache, mock_process_catalog_request, mock_encryption_service, mock_apply_rpdb_posters
    ):
        """Test LRU cache hit."""
        # Set up cache hit
        cached_data = {"metas": [{"name": "Cached Movie", "id": "cached-id"}]}
        mock_cache.aget.return_value = cached_data

        result = await _cached_catalog("test_config", ContentType.MOVIE, "trending_movie")

        # Verify cache get
        mock_cache.aget.assert_called_once()

        # Verify _process_catalog_request_internal was not called
        mock_process_catalog_request.assert_not_called()

        # Verify result is from cache
        assert result == cached_data

        # Verify no cache set
        mock_cache.aset.assert_not_called()

    @pytest.mark.asyncio
    async def test_redis_cache_skip_zero(
        self, mock_cache, mock_process_catalog_request, mock_encryption_service, mock_apply_rpdb_posters
    ):
        """Test Redis cache behavior with skip=0."""
        # Set up Redis cache
        mock_cache.is_redis = True
        mock_cache.aget.return_value = None

        result = await _cached_catalog("test_config", ContentType.MOVIE, "trending_movie")

        # Verify cache key format
        cache_key_arg = mock_cache.aget.call_args[0][0]
        assert cache_key_arg == "catalog:trending_movie"

        # Verify _process_catalog_request_internal was called
        mock_process_catalog_request.assert_called_once()

        # Verify result
        assert result == {"metas": [{"name": "Test Movie", "id": "test-id"}]}

        # Verify cache set
        mock_cache.aset.assert_called_once()

    @pytest.mark.asyncio
    async def test_redis_cache_with_existing_entries(
        self, mock_cache, mock_process_catalog_request, mock_encryption_service, mock_apply_rpdb_posters
    ):
        """Test Redis cache with existing entries."""
        # Set up Redis cache with existing entries
        mock_cache.is_redis = True
        existing_entries = {
            "metas": [
                {"name": "Existing Movie 1", "id": "existing-1"},
                {"name": "Existing Movie 2", "id": "existing-2"},
            ]
        }
        mock_cache.aget.return_value = existing_entries

        # New entries to be added
        new_entries = {"metas": [{"name": "New Movie", "id": "new-id"}]}
        mock_process_catalog_request.return_value = new_entries

        result = await _cached_catalog("test_config", ContentType.MOVIE, "trending_movie", skip=100)

        # With only 2 existing entries and skip=100 (adjusted to 0), we need more entries
        # Should generate new entries since we don't have enough cached entries
        mock_process_catalog_request.assert_called_once()

        # Should return combined entries (existing + new)
        assert result == {
            "metas": [
                {"name": "Existing Movie 1", "id": "existing-1"},
                {"name": "Existing Movie 2", "id": "existing-2"},
                {"name": "New Movie", "id": "new-id"},
            ]
        }

    @pytest.mark.asyncio
    async def test_redis_cache_pagination(
        self, mock_cache, mock_process_catalog_request, mock_encryption_service, mock_apply_rpdb_posters
    ):
        """Test Redis cache pagination."""
        # Set up Redis cache
        mock_cache.is_redis = True

        # Set up existing entries
        existing_entries = {"metas": [{"name": f"Movie {i}", "id": f"id-{i}"} for i in range(1, 11)]}
        mock_cache.aget.return_value = existing_entries

        # Request with skip=110 (adjusted to 10)
        result = await _cached_catalog("test_config", ContentType.MOVIE, "trending_movie", skip=110)

        # Since adjusted_skip (10) == total_entries (10), should generate new entries
        mock_process_catalog_request.assert_called_once()

        # Verify enhanced prompt includes existing entries
        prompt_arg = mock_process_catalog_request.call_args[0][1]
        assert "Avoid recommending these already suggested titles" in prompt_arg
        for i in range(1, 11):
            assert f"Movie {i}" in prompt_arg

        # Verify cache was updated with combined entries
        mock_cache.aset.assert_called_once()
        # Don't check exact key format, but verify the value contains both existing and new entries
        assert len(mock_cache.aset.call_args[0][1]["metas"]) == 11  # 10 existing + 1 new

        # Verify result contains all entries (existing + new)
        expected_metas = [{"name": f"Movie {i}", "id": f"id-{i}"} for i in range(1, 11)]
        expected_metas.append({"name": "Test Movie", "id": "test-id"})
        assert result == {"metas": expected_metas}

    @pytest.mark.asyncio
    async def test_redis_cache_max_entries(
        self, mock_cache, mock_process_catalog_request, mock_encryption_service, mock_apply_rpdb_posters
    ):
        """Test Redis cache with maximum entries reached."""
        # Set up Redis cache
        mock_cache.is_redis = True

        # Set up existing entries at max capacity
        with patch("app.api.stremio.settings") as mock_settings:
            mock_settings.MAX_CATALOG_ENTRIES = 10
            mock_settings.MAX_CATALOG_RESULTS = 20

            existing_entries = {"metas": [{"name": f"Movie {i}", "id": f"id-{i}"} for i in range(1, 11)]}
            mock_cache.aget.return_value = existing_entries

            # Request with skip beyond existing entries
            result = await _cached_catalog("test_config", ContentType.MOVIE, "trending_movie", skip=200)

            # Should not generate new entries since max is reached
            mock_process_catalog_request.assert_not_called()

            # Should return existing entries
            assert result == {"metas": existing_entries["metas"]}

    @pytest.mark.asyncio
    async def test_catalog_id_fallback(
        self, mock_cache, mock_process_catalog_request, mock_encryption_service, mock_apply_rpdb_posters
    ):
        """Test fallback to trending when catalog_id is invalid."""
        # Set up cache miss
        mock_cache.aget.return_value = None

        # Invalid catalog_id
        await _cached_catalog("test_config", ContentType.MOVIE, "invalid_catalog")

        # Verify _process_catalog_request_internal was called
        mock_process_catalog_request.assert_called_once()

        # Verify trending prompt was used
        prompt_arg = mock_process_catalog_request.call_args[0][1]
        assert "trending" in prompt_arg.lower()

    @pytest.mark.asyncio
    async def test_duplicate_filtering(
        self, mock_cache, mock_process_catalog_request, mock_encryption_service, mock_apply_rpdb_posters
    ):
        """Test filtering of duplicate entries in Redis cache."""
        # Set up Redis cache
        mock_cache.is_redis = True

        # Set up existing entries
        existing_entries = {"metas": [{"name": "Existing Movie", "id": "existing-id"}]}
        mock_cache.aget.return_value = existing_entries

        # New entries with a duplicate
        new_entries = {
            "metas": [
                {"name": "Existing Movie", "id": "duplicate-id"},  # Same name, different ID
                {"name": "New Movie", "id": "new-id"},
            ]
        }
        mock_process_catalog_request.return_value = new_entries

        # Request with skip beyond existing entries
        with patch("app.api.stremio.settings") as mock_settings:
            mock_settings.MAX_CATALOG_RESULTS = 5
            mock_settings.MAX_CATALOG_ENTRIES = 100

            result = await _cached_catalog("test_config", ContentType.MOVIE, "trending_movie", skip=110)

            # Verify only non-duplicate entry was added
            expected_combined = {
                "metas": [{"name": "Existing Movie", "id": "existing-id"}, {"name": "New Movie", "id": "new-id"}]
            }
            mock_cache.aset.assert_called_once()
            assert mock_cache.aset.call_args[0][1] == expected_combined

            # Verify result contains all entries (existing + new non-duplicate)
            assert result == {
                "metas": [{"name": "Existing Movie", "id": "existing-id"}, {"name": "New Movie", "id": "new-id"}]
            }
