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
        assert len(manifest["catalogs"]) == 2
        assert isinstance(manifest["catalogs"], list)

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
        assert len(manifest["catalogs"]) == 1
        assert manifest["catalogs"][0]["type"] == "movie"

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
        assert len(manifest["catalogs"]) == 1
        assert manifest["catalogs"][0]["type"] == "series"

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

        response = client.get("/config/encrypted_config/movie/catalog/movie/test_catalog.json")

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

        response = client.get("/config/encrypted_config/series/catalog/series/test_catalog.json")

        assert response.status_code == 200
        data = response.json()
        assert "metas" in data
