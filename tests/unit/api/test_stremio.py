"""
Tests for the Stremio API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.api.deps import get_config
from app.models.config import Config
from app.core.config import settings


@pytest.fixture
def client():
    """Fixture providing a TestClient instance (no dependency override)."""
    app.dependency_overrides.pop(get_config, None)
    return TestClient(app)


@pytest.fixture
def client_with_cfg():
    """Fixture providing a TestClient with get_config override (happy-path)."""
    app.dependency_overrides[get_config] = lambda: Config()
    return TestClient(app)


class TestStremioRouter:
    """Tests for the Stremio router endpoints."""

    def test_get_manifest(self, client_with_cfg):
        """Test the manifest endpoint returns valid combined structure."""
        response = client_with_cfg.get("/config/encrypted_config/manifest.json")

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

    def test_get_manifest_invalid_config(self, client):
        """Test the manifest endpoint with an invalid config."""
        # Mock the encryption service to raise an exception
        response = client.get("/config/invalid_config/manifest.json")

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_get_movie_manifest(self, client_with_cfg):
        """Test the dedicated movie manifest endpoint."""
        response = client_with_cfg.get("/config/encrypted_config/movie/manifest.json")

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

    def test_get_series_manifest(self, client_with_cfg):
        """Test the dedicated series manifest endpoint."""
        response = client_with_cfg.get("/config/encrypted_config/series/manifest.json")

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

    def test_get_movie_manifest_invalid_config(
        self,
        client,
    ):
        """Test the movie manifest endpoint with invalid config."""

        response = client.get("/config/invalid_config/movie/manifest.json")

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_get_series_manifest_invalid_config(
        self,
        client,
    ):
        """Test the series manifest endpoint with invalid config."""

        response = client.get("/config/invalid_config/series/manifest.json")

        assert response.status_code == 400
        assert "detail" in response.json()

    def test_get_movie_catalog_route(
        self,
        client_with_cfg,
    ):
        """Test the movie-specific catalog route."""
        # Use a valid catalog ID from CATALOG_PROMPTS
        response = client_with_cfg.get("/config/encrypted_config/catalog/movie/trending_movie.json")

        assert response.status_code == 200
        data = response.json()
        assert "metas" in data

    def test_get_series_catalog_route(
        self,
        client_with_cfg,
    ):
        """Test the series-specific catalog route."""
        # Use a valid catalog ID from CATALOG_PROMPTS
        response = client_with_cfg.get("/config/encrypted_config/catalog/series/trending_series.json")

        assert response.status_code == 200
        data = response.json()
        assert "metas" in data
