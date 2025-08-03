"""
Tests for the Stremio API endpoints.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.models.config import Config
from app.core.config import settings


@pytest.fixture
def client():
    """Fixture providing a TestClient instance."""
    return TestClient(app)


@pytest.fixture
def mock_encryption_service():
    """Fixture providing a mocked EncryptionService."""
    with patch("app.api.stremio.encryption_service") as mock:
        yield mock


class TestStremioRouter:
    """Tests for the Stremio router endpoints."""

    def test_get_manifest(self, client, mock_encryption_service):
        """Test the manifest endpoint returns valid combined structure."""
        # Mock the encryption service to return a valid config
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()

        response = client.get("/config/encrypted_config/manifest.json")

        assert response.status_code == 200
        manifest = response.json()
        assert manifest["id"] == settings.STREMIO_ADDON_ID
        assert manifest["name"] == "AI Companion"
        assert manifest["types"] == ["movie", "series"]
        # Don't assert exact number of catalogs as it depends on ENABLE_FEED_CATALOGS
        assert len(manifest["catalogs"]) >= 2
        assert isinstance(manifest["catalogs"], list)
        
        # Check that we have at least one movie and one series catalog
        movie_catalogs = [c for c in manifest["catalogs"] if c["type"] == "movie"]
        series_catalogs = [c for c in manifest["catalogs"] if c["type"] == "series"]
        assert len(movie_catalogs) >= 1
        assert len(series_catalogs) >= 1

    def test_get_manifest_invalid_config(self, client, mock_encryption_service):
        """Test the manifest endpoint with an invalid config."""
        # Mock the encryption service to raise an exception
        mock_encryption_service.decrypt.side_effect = Exception("Invalid config")

        response = client.get("/config/invalid_config/manifest.json")

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_get_movie_manifest(self, client, mock_encryption_service):
        """Test the dedicated movie manifest endpoint."""
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()

        response = client.get("/config/encrypted_config/movie/manifest.json")

        assert response.status_code == 200
        manifest = response.json()
        assert manifest["id"] == f"{settings.STREMIO_ADDON_ID}-movie"
        assert manifest["name"] == "AI Movie Companion"
        assert manifest["types"] == ["movie"]
        # Don't assert exact number of catalogs as it depends on ENABLE_FEED_CATALOGS
        assert len(manifest["catalogs"]) >= 1
        # Check that all catalogs are movie type
        for catalog in manifest["catalogs"]:
            assert catalog["type"] == "movie"

    def test_get_series_manifest(self, client, mock_encryption_service):
        """Test the dedicated series manifest endpoint."""
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()

        response = client.get("/config/encrypted_config/series/manifest.json")

        assert response.status_code == 200
        manifest = response.json()
        assert manifest["id"] == f"{settings.STREMIO_ADDON_ID}-series"
        assert manifest["name"] == "AI Series Companion"
        assert manifest["types"] == ["series"]
        # Don't assert exact number of catalogs as it depends on ENABLE_FEED_CATALOGS
        assert len(manifest["catalogs"]) >= 1
        # Check that all catalogs are series type
        for catalog in manifest["catalogs"]:
            assert catalog["type"] == "series"

    def test_get_movie_manifest_invalid_config(self, client, mock_encryption_service):
        """Test the movie manifest endpoint with invalid config."""
        mock_encryption_service.decrypt.side_effect = Exception("Invalid config")

        response = client.get("/config/invalid_config/movie/manifest.json")

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_get_series_manifest_invalid_config(self, client, mock_encryption_service):
        """Test the series manifest endpoint with invalid config."""
        mock_encryption_service.decrypt.side_effect = Exception("Invalid config")

        response = client.get("/config/invalid_config/series/manifest.json")

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_get_movie_catalog_route(self, client, mock_encryption_service):
        """Test the movie-specific catalog route."""
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()

        # Use a valid catalog ID from CATALOG_PROMPTS
        response = client.get("/config/encrypted_config/catalog/movie/trending_movie.json")

        assert response.status_code == 200
        data = response.json()
        assert "metas" in data

    def test_get_series_catalog_route(self, client, mock_encryption_service):
        """Test the series-specific catalog route."""
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()

        # Use a valid catalog ID from CATALOG_PROMPTS
        response = client.get("/config/encrypted_config/catalog/series/trending_series.json")

        assert response.status_code == 200
        data = response.json()
        assert "metas" in data
