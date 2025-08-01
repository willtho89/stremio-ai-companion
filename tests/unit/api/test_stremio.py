"""
Tests for the Stremio API endpoints.
"""

import pytest
import json
from unittest.mock import patch, MagicMock, AsyncMock
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
    with patch('app.api.stremio.encryption_service') as mock:
        yield mock


@pytest.fixture
def mock_llm_service():
    """Fixture providing a mocked LLMService."""
    with patch('app.api.stremio.LLMService') as mock:
        mock_instance = MagicMock()
        mock_instance.generate_movie_suggestions = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_tmdb_service():
    """Fixture providing a mocked TMDBService."""
    with patch('app.api.stremio.TMDBService') as mock:
        mock_instance = MagicMock()
        mock_instance.search_movie = AsyncMock()
        mock_instance.get_movie_details = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_rpdb_service():
    """Fixture providing a mocked RPDBService."""
    with patch('app.api.stremio.RPDBService') as mock:
        mock_instance = MagicMock()
        mock_instance.get_poster = AsyncMock()
        mock.return_value = mock_instance
        yield mock_instance


class TestStremioRouter:
    """Tests for the Stremio router endpoints."""

    def test_get_manifest(self, client, mock_encryption_service):
        """Test the manifest endpoint."""
        # Mock the encryption service to return a valid config
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890"
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()
        
        response = client.get("/config/encrypted_config/manifest.json")
        
        assert response.status_code == 200
        assert response.json()["id"] == "ai.companion.stremio"
        assert response.json()["name"] == "AI Companion"
        assert "catalogs" in response.json()
        mock_encryption_service.decrypt.assert_called_once_with("encrypted_config")

    def test_get_manifest_invalid_config(self, client, mock_encryption_service):
        """Test the manifest endpoint with an invalid config."""
        # Mock the encryption service to raise an exception
        mock_encryption_service.decrypt.side_effect = Exception("Invalid config")
        
        response = client.get("/config/invalid_config/manifest.json")
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid config"
        mock_encryption_service.decrypt.assert_called_once_with("invalid_config")

    @patch('app.api.stremio._process_catalog_request')
    async def test_get_catalog(self, mock_process, client):
        """Test the catalog endpoint."""
        # Mock the _process_catalog_request function
        mock_process.return_value = {"metas": [{"id": "tmdb:123", "name": "Test Movie"}]}
        
        response = client.get("/config/encrypted_config/catalog/movie/ai_companion_movie.json")
        
        assert response.status_code == 200
        assert response.json()["metas"][0]["id"] == "tmdb:123"
        assert response.json()["metas"][0]["name"] == "Test Movie"
        mock_process.assert_called_once_with("encrypted_config", "ai_companion_movie", None)

    @patch('app.api.stremio._process_catalog_request')
    async def test_get_catalog_with_search(self, mock_process, client):
        """Test the catalog endpoint with a search parameter."""
        # Mock the _process_catalog_request function
        mock_process.return_value = {"metas": [{"id": "tmdb:123", "name": "Test Movie"}]}
        
        response = client.get("/config/encrypted_config/catalog/movie/ai_companion_movie.json?search=test")
        
        assert response.status_code == 200
        assert response.json()["metas"][0]["id"] == "tmdb:123"
        assert response.json()["metas"][0]["name"] == "Test Movie"
        mock_process.assert_called_once_with("encrypted_config", "ai_companion_movie", "test")

    @patch('app.api.stremio._process_catalog_request')
    async def test_get_catalog_search(self, mock_process, client):
        """Test the catalog search endpoint."""
        # Mock the _process_catalog_request function
        mock_process.return_value = {"metas": [{"id": "tmdb:123", "name": "Test Movie"}]}
        
        response = client.get("/config/encrypted_config/catalog/movie/ai_companion_movie/search=test.json")
        
        assert response.status_code == 200
        assert response.json()["metas"][0]["id"] == "tmdb:123"
        assert response.json()["metas"][0]["name"] == "Test Movie"
        mock_process.assert_called_once_with("encrypted_config", "ai_companion_movie", "test")

    async def test_process_catalog_request(
        self, 
        mock_encryption_service, 
        mock_llm_service, 
        mock_tmdb_service, 
        mock_rpdb_service
    ):
        """Test the _process_catalog_request function."""
        # Import the function directly for testing
        from app.api.stremio import _process_catalog_request
        
        # Mock the encryption service to return a valid config
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
            use_posterdb=True,
            posterdb_api_key="rpdb-test1234567890"
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()
        
        # Mock the LLM service to return movie suggestions
        mock_llm_service.generate_movie_suggestions.return_value = [
            "The Matrix (1999)",
            "Inception (2010)"
        ]
        
        # Mock the TMDB service to return movie data
        mock_tmdb_service.search_movie.side_effect = [
            {"id": 123, "title": "The Matrix"},
            {"id": 456, "title": "Inception"}
        ]
        mock_tmdb_service.get_movie_details.side_effect = [
            {
                "id": 123, 
                "title": "The Matrix", 
                "external_ids": {"imdb_id": "tt0133093"}
            },
            {
                "id": 456, 
                "title": "Inception", 
                "external_ids": {"imdb_id": "tt1375666"}
            }
        ]
        
        # Mock the RPDB service to return poster URLs
        mock_rpdb_service.get_poster.side_effect = [
            "https://example.com/poster1.jpg",
            "https://example.com/poster2.jpg"
        ]
        
        # Call the function
        result = await _process_catalog_request("encrypted_config", "ai_companion_movie", "test")
        
        # Verify the result
        assert len(result["metas"]) == 2
        assert result["metas"][0]["id"] == "tmdb:123"
        assert result["metas"][0]["name"] == "The Matrix"
        assert result["metas"][0]["poster"] == "https://example.com/poster1.jpg"
        assert result["metas"][1]["id"] == "tmdb:456"
        assert result["metas"][1]["name"] == "Inception"
        assert result["metas"][1]["poster"] == "https://example.com/poster2.jpg"
        
        # Verify the service calls
        mock_encryption_service.decrypt.assert_called_once_with("encrypted_config")
        mock_llm_service.generate_movie_suggestions.assert_called_once_with("test", config.max_results)
        assert mock_tmdb_service.search_movie.call_count == 2
        assert mock_tmdb_service.get_movie_details.call_count == 2
        assert mock_rpdb_service.get_poster.call_count == 2

    async def test_process_catalog_request_without_rpdb(
        self, 
        mock_encryption_service, 
        mock_llm_service, 
        mock_tmdb_service
    ):
        """Test the _process_catalog_request function without RPDB."""
        # Import the function directly for testing
        from app.api.stremio import _process_catalog_request
        
        # Mock the encryption service to return a valid config without RPDB
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
            use_posterdb=False,
            posterdb_api_key=None
        )
        mock_encryption_service.decrypt.return_value = config.model_dump_json()
        
        # Mock the LLM service to return movie suggestions
        mock_llm_service.generate_movie_suggestions.return_value = [
            "The Matrix (1999)"
        ]
        
        # Mock the TMDB service to return movie data
        mock_tmdb_service.search_movie.return_value = {"id": 123, "title": "The Matrix"}
        mock_tmdb_service.get_movie_details.return_value = {
            "id": 123, 
            "title": "The Matrix", 
            "poster_path": "/path/to/poster.jpg",
            "external_ids": {"imdb_id": "tt0133093"}
        }
        
        # Call the function
        result = await _process_catalog_request("encrypted_config", "ai_companion_movie", "test")
        
        # Verify the result
        assert len(result["metas"]) == 1
        assert result["metas"][0]["id"] == "tmdb:123"
        assert result["metas"][0]["name"] == "The Matrix"
        assert result["metas"][0]["poster"] == "https://image.tmdb.org/t/p/w500/path/to/poster.jpg"
        
        # Verify the service calls
        mock_encryption_service.decrypt.assert_called_once_with("encrypted_config")
        mock_llm_service.generate_movie_suggestions.assert_called_once_with("test", config.max_results)
        mock_tmdb_service.search_movie.assert_called_once()
        mock_tmdb_service.get_movie_details.assert_called_once_with(123)

    async def test_process_catalog_request_with_error(
        self, 
        mock_encryption_service, 
        mock_llm_service
    ):
        """Test the _process_catalog_request function with an error."""
        # Import the function directly for testing
        from app.api.stremio import _process_catalog_request
        
        # Mock the encryption service to raise an exception
        mock_encryption_service.decrypt.side_effect = Exception("Invalid config")
        
        # Call the function and expect an exception
        with pytest.raises(Exception) as exc_info:
            await _process_catalog_request("invalid_config", "ai_companion_movie", "test")
        
        assert "Invalid config" in str(exc_info.value)
        mock_encryption_service.decrypt.assert_called_once_with("invalid_config")
        mock_llm_service.generate_movie_suggestions.assert_not_called()