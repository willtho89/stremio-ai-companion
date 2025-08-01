"""
Tests for the RPDB service.
"""

import pytest

from app.services.rpdb import RPDBService


class TestRPDBService:
    """Tests for the RPDBService class."""

    @pytest.fixture
    def rpdb_service(self):
        """Fixture providing an RPDBService instance."""
        return RPDBService("test-api-key")

    def test_init(self):
        """Test initialization of RPDBService."""
        service = RPDBService("test-api-key")

        assert service.api_key == "test-api-key"

    async def test_get_poster_with_valid_imdb_id(self, rpdb_service):
        """Test getting a poster URL with a valid IMDB ID."""
        poster_url = await rpdb_service.get_poster("tt0137523")

        assert poster_url == "https://api.ratingposterdb.com/test-api-key/imdb/poster-default/tt0137523.jpg"

    async def test_get_poster_with_imdb_id_without_tt_prefix(self, rpdb_service):
        """Test getting a poster URL with an IMDB ID without 'tt' prefix."""
        poster_url = await rpdb_service.get_poster("0137523")

        assert poster_url == "https://api.ratingposterdb.com/test-api-key/imdb/poster-default/tt0137523.jpg"

    async def test_get_poster_with_empty_imdb_id(self, rpdb_service):
        """Test getting a poster URL with an empty IMDB ID."""
        poster_url = await rpdb_service.get_poster("")

        assert poster_url is None

    async def test_get_poster_with_none_imdb_id(self, rpdb_service):
        """Test getting a poster URL with None as IMDB ID."""
        poster_url = await rpdb_service.get_poster(None)

        assert poster_url is None

    async def test_get_poster_with_empty_api_key(self):
        """Test getting a poster URL with an empty API key."""
        service = RPDBService("")
        poster_url = await service.get_poster("tt0137523")

        assert poster_url is None

    async def test_get_poster_with_none_api_key(self):
        """Test getting a poster URL with None as API key."""
        service = RPDBService(None)
        poster_url = await service.get_poster("tt0137523")

        assert poster_url is None
