"""
Tests for the LLM service.
"""

import json
from unittest.mock import patch, MagicMock

import openai
import pytest

from app.services.llm import LLMService


class TestLLMService:
    """Tests for the LLMService class."""

    @pytest.fixture
    def llm_service(self, sample_config):
        """Fixture providing an LLMService instance."""
        return LLMService(sample_config)

    @patch("openai.OpenAI")
    def test_init(self, mock_openai, sample_config):
        """Test initialization of LLMService."""
        LLMService(sample_config)

        mock_openai.assert_called_once_with(
            api_key=sample_config.openai_api_key, base_url=sample_config.openai_base_url
        )

    async def test_generate_movie_suggestions_structured_output(self, sample_movie_suggestions, sample_config):
        """Test generating movie suggestions with structured output."""
        with patch("openai.OpenAI") as mock_openai:
            # Mock the OpenAI client and response
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Create a mock response for the structured output
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.parsed = sample_movie_suggestions
            mock_client.beta.chat.completions.parse.return_value = mock_response

            # Create service with mocked client
            llm_service = LLMService(sample_config)

            # Call the method
            result = await llm_service.generate_movie_suggestions("Give me some good movies", 5)

            # Verify the result
            assert result == sample_movie_suggestions.movies
            assert len(result) == 5
            assert result[0] == "The Shawshank Redemption (1994)"

            # Verify the API was called correctly
            mock_client.beta.chat.completions.parse.assert_called_once()
            args, kwargs = mock_client.beta.chat.completions.parse.call_args
            assert kwargs["model"] == "gpt-4.1-mini"
            assert kwargs["temperature"] == 0.7
            assert kwargs["max_tokens"] == 500
            assert kwargs["timeout"] == 30

    async def test_generate_movie_suggestions_fallback(self, sample_config):
        """Test generating movie suggestions with fallback to regular completion."""
        with patch("openai.OpenAI") as mock_openai:
            # Mock the OpenAI client and responses
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Make the structured output fail
            mock_client.beta.chat.completions.parse.side_effect = openai.BadRequestError(
                message="Model does not support this format", response=MagicMock(), body={}
            )

            # Create a mock response for the fallback
            mock_fallback_response = MagicMock()
            mock_fallback_response.choices = [MagicMock()]
            mock_fallback_response.choices[0].message.content = json.dumps(
                [
                    "The Godfather (1972)",
                    "The Shawshank Redemption (1994)",
                    "The Dark Knight (2008)",
                    "Pulp Fiction (1994)",
                    "Inception (2010)",
                ]
            )
            mock_client.chat.completions.create.return_value = mock_fallback_response

            # Create service with mocked client
            llm_service = LLMService(sample_config)

            # Call the method
            result = await llm_service.generate_movie_suggestions("Give me some good movies", 5)

            # Verify the result
            assert len(result) == 5
            assert result[0] == "The Godfather (1972)"

            # Verify both APIs were called
            mock_client.beta.chat.completions.parse.assert_called_once()
            mock_client.chat.completions.create.assert_called_once()

    @patch("openai.OpenAI")
    async def test_generate_movie_suggestions_json_error(self, mock_openai, llm_service):
        """Test handling JSON decode error in fallback."""
        # Mock the OpenAI client and responses
        mock_client = MagicMock()
        mock_openai.return_value = mock_client

        # Make the structured output fail
        mock_client.beta.chat.completions.parse.side_effect = openai.BadRequestError(
            message="Model does not support this format", response=MagicMock(), body={}
        )

        # Create a mock response with invalid JSON
        mock_fallback_response = MagicMock()
        mock_fallback_response.choices = [MagicMock()]
        mock_fallback_response.choices[0].message.content = "Not valid JSON"
        mock_client.chat.completions.create.return_value = mock_fallback_response

        # Call the method
        result = await llm_service.generate_movie_suggestions("Give me some good movies", 5)

        # Verify the fallback behavior
        assert len(result) == 1
        assert result[0] == "Give me some good movies"

    async def test_generate_movie_suggestions_api_error(self, sample_config):
        """Test handling OpenAI API error."""
        with patch("openai.OpenAI") as mock_openai:
            # Mock the OpenAI client and responses
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Make the API call fail
            mock_client.beta.chat.completions.parse.side_effect = Exception("API error")

            # Create service with mocked client
            llm_service = LLMService(sample_config)

            # Call the method
            result = await llm_service.generate_movie_suggestions("Give me some good movies", 5)

            # Verify the fallback behavior
            assert len(result) == 1
            assert result[0] == "Give me some good movies"

    async def test_generate_movie_suggestions_with_year(self, sample_movie_suggestions, sample_config):
        """Test generating movie suggestions with a year in the query."""
        with patch("openai.OpenAI") as mock_openai:
            # Mock the OpenAI client and response
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Create a mock response for the structured output
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.parsed = sample_movie_suggestions
            mock_client.beta.chat.completions.parse.return_value = mock_response

            # Create service with mocked client
            llm_service = LLMService(sample_config)

            # Call the method with a query containing a year
            result = await llm_service.generate_movie_suggestions("The Matrix (1999)", 5)

            # Verify the result
            assert result == sample_movie_suggestions.movies

            # Verify the API was called with the appropriate prompt for a specific movie
            args, kwargs = mock_client.beta.chat.completions.parse.call_args
            assert "The Matrix" in kwargs["messages"][0]["content"]
            assert "1999" in kwargs["messages"][0]["content"]
