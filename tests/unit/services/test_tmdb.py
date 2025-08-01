"""
Tests for the TMDB service.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from app.services.tmdb import TMDBService


class TestTMDBService:
    """Tests for the TMDBService class."""

    @pytest.fixture
    def tmdb_service(self):
        """Fixture providing a TMDBService instance."""
        return TMDBService("test-token")

    def test_init(self):
        """Test initialization of TMDBService."""
        service = TMDBService("test-token")
        
        assert service.read_access_token == "test-token"
        assert service.base_url == "https://api.themoviedb.org/3"

    def test_get_headers(self):
        """Test the _get_headers method."""
        service = TMDBService("test-token")
        headers = service._get_headers()
        
        assert headers["accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test-token"

    @patch('httpx.AsyncClient.get')
    async def test_search_movie_success(self, mock_get, tmdb_service):
        """Test successful movie search."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 550,
                    "title": "Fight Club",
                    "release_date": "1999-10-15"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = await tmdb_service.search_movie("Fight Club")
        
        # Verify the result
        assert result["id"] == 550
        assert result["title"] == "Fight Club"
        
        # Verify the API was called correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://api.themoviedb.org/3/search/movie"
        assert kwargs["params"]["query"] == "Fight Club"
        assert kwargs["params"]["include_adult"] == "false"

    @patch('httpx.AsyncClient.get')
    async def test_search_movie_with_year(self, mock_get, tmdb_service):
        """Test movie search with year filter."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 550,
                    "title": "Fight Club",
                    "release_date": "1999-10-15"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = await tmdb_service.search_movie("Fight Club", 1999)
        
        # Verify the API was called with year filter
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["primary_release_year"] == "1999"

    @patch('httpx.AsyncClient.get')
    async def test_search_movie_with_adult_content(self, mock_get, tmdb_service):
        """Test movie search with adult content included."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "id": 550,
                    "title": "Fight Club",
                    "release_date": "1999-10-15"
                }
            ]
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = await tmdb_service.search_movie("Fight Club", include_adult=True)
        
        # Verify the API was called with adult content included
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs["params"]["include_adult"] == "true"

    @patch('httpx.AsyncClient.get')
    async def test_search_movie_no_results(self, mock_get, tmdb_service):
        """Test movie search with no results."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"results": []}
        mock_get.return_value = mock_response
        
        # Call the method
        result = await tmdb_service.search_movie("Nonexistent Movie")
        
        # Verify the result
        assert result is None

    @patch('httpx.AsyncClient.get')
    async def test_search_movie_timeout(self, mock_get, tmdb_service):
        """Test movie search with timeout."""
        # Mock the timeout exception
        mock_get.side_effect = httpx.TimeoutException("Timeout")
        
        # Call the method
        result = await tmdb_service.search_movie("Fight Club")
        
        # Verify the result
        assert result is None

    @patch('httpx.AsyncClient.get')
    async def test_search_movie_http_error(self, mock_get, tmdb_service):
        """Test movie search with HTTP error."""
        # Mock the HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response
        
        # Call the method
        result = await tmdb_service.search_movie("Fight Club")
        
        # Verify the result
        assert result is None

    @patch('httpx.AsyncClient.get')
    async def test_get_movie_details_success(self, mock_get, tmdb_service):
        """Test successful movie details retrieval."""
        # Mock the response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": 550,
            "title": "Fight Club",
            "overview": "A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression into a shocking new form of therapy.",
            "release_date": "1999-10-15",
            "external_ids": {
                "imdb_id": "tt0137523"
            }
        }
        mock_get.return_value = mock_response
        
        # Call the method
        result = await tmdb_service.get_movie_details(550)
        
        # Verify the result
        assert result["id"] == 550
        assert result["title"] == "Fight Club"
        assert result["external_ids"]["imdb_id"] == "tt0137523"
        
        # Verify the API was called correctly
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert args[0] == "https://api.themoviedb.org/3/movie/550"
        assert kwargs["params"]["append_to_response"] == "external_ids"

    @patch('httpx.AsyncClient.get')
    async def test_get_movie_details_timeout(self, mock_get, tmdb_service):
        """Test movie details retrieval with timeout."""
        # Mock the timeout exception
        mock_get.side_effect = httpx.TimeoutException("Timeout")
        
        # Call the method
        result = await tmdb_service.get_movie_details(550)
        
        # Verify the result
        assert result is None

    @patch('httpx.AsyncClient.get')
    async def test_get_movie_details_http_error(self, mock_get, tmdb_service):
        """Test movie details retrieval with HTTP error."""
        # Mock the HTTP error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_response
        )
        mock_get.return_value = mock_response
        
        # Call the method
        result = await tmdb_service.get_movie_details(550)
        
        # Verify the result
        assert result is None