"""
Tests for the Stremio API endpoints.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.models.config import Config


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
        """Test the manifest endpoint returns valid structure."""
        # Mock the encryption service to return a valid config
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()

        response = client.get("/config/encrypted_config/manifest.json")

        assert response.status_code == 200
        manifest = response.json()
        assert "id" in manifest
        assert "name" in manifest
        assert "catalogs" in manifest
        assert isinstance(manifest["catalogs"], list)

    def test_get_manifest_invalid_config(self, client, mock_encryption_service):
        """Test the manifest endpoint with an invalid config."""
        # Mock the encryption service to raise an exception
        mock_encryption_service.decrypt.side_effect = Exception("Invalid config")

        response = client.get("/config/invalid_config/manifest.json")

        assert response.status_code == 400
        assert "detail" in response.json()
