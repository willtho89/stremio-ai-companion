"""
Integration tests for the movie suggestions workflow.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.models.config import Config
from app.services.encryption import EncryptionService


@pytest.fixture
def client():
    """Fixture providing a TestClient instance."""
    return TestClient(app)


@pytest.fixture
def encrypted_config():
    """Fixture providing an encrypted config for testing."""
    config = Config(
        openai_api_key="sk-test123456789012345678901234567890",
        tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        max_results=5,
    )
    # Use the default encryption key from settings
    service = EncryptionService("stremio-ai-companion-default-key")
    return service.encrypt(config.model_dump_json())


@pytest.mark.integration
class TestMovieSuggestionsWorkflow:
    """Integration tests for the movie suggestions workflow."""

    @patch("app.services.encryption.EncryptionService.decrypt")
    async def test_invalid_config(self, mock_decrypt, client):
        """Test the workflow with an invalid config."""
        # Mock the encryption service to raise an exception
        mock_decrypt.side_effect = Exception("Invalid config")

        # Make the request to the catalog endpoint
        response = client.get("/config/invalid_config/catalog/movie/ai_companion_movie.json?search=sci-fi movies")

        # Verify the response
        assert response.status_code == 500
        assert "Invalid config" in response.json()["detail"]
        mock_decrypt.assert_called_once_with("invalid_config")
