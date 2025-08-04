"""
Tests for duplicate filtering in LLM service.
"""

from unittest.mock import AsyncMock

import pytest

from app.models.config import Config
from app.models.movie import MovieSuggestion, TVSeriesSuggestion
from app.services.llm import LLMService


class TestLLMDuplicateFiltering:
    """Test duplicate filtering functionality in LLM service."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )

    @pytest.fixture
    def llm_service(self, config):
        """Create an LLM service instance."""
        return LLMService(config)

    def test_filter_duplicates_movies(self, llm_service):
        """Test filtering duplicate movie suggestions."""
        suggestions = [
            MovieSuggestion(title="The Matrix", year=1999),
            MovieSuggestion(title="The Matrix", year=1999),  # Exact duplicate
            MovieSuggestion(title="the matrix", year=1999),  # Case difference
            MovieSuggestion(title=" The Matrix ", year=1999),  # Whitespace difference
            MovieSuggestion(title="The Matrix Reloaded", year=2003),  # Different movie
            MovieSuggestion(title="The Matrix", year=2021),  # Same title, different year
        ]

        filtered = llm_service._filter_duplicates(suggestions)

        assert len(filtered) == 3
        assert filtered[0].title == "The Matrix" and filtered[0].year == 1999
        assert filtered[1].title == "The Matrix Reloaded" and filtered[1].year == 2003
        assert filtered[2].title == "The Matrix" and filtered[2].year == 2021

    def test_filter_duplicates_tv_series(self, llm_service):
        """Test filtering duplicate TV series suggestions."""
        suggestions = [
            TVSeriesSuggestion(title="Breaking Bad", year=2008),
            TVSeriesSuggestion(title="Breaking Bad", year=2008),  # Exact duplicate
            TVSeriesSuggestion(title="BREAKING BAD", year=2008),  # Case difference
            TVSeriesSuggestion(title="Better Call Saul", year=2015),  # Different series
        ]

        filtered = llm_service._filter_duplicates(suggestions)

        assert len(filtered) == 2
        assert filtered[0].title == "Breaking Bad" and filtered[0].year == 2008
        assert filtered[1].title == "Better Call Saul" and filtered[1].year == 2015

    def test_filter_duplicates_preserves_order(self, llm_service):
        """Test that filtering preserves the original order."""
        suggestions = [
            MovieSuggestion(title="Movie C", year=2020),
            MovieSuggestion(title="Movie A", year=2018),
            MovieSuggestion(title="Movie B", year=2019),
            MovieSuggestion(title="Movie A", year=2018),  # Duplicate
        ]

        filtered = llm_service._filter_duplicates(suggestions)

        assert len(filtered) == 3
        assert filtered[0].title == "Movie C"
        assert filtered[1].title == "Movie A"
        assert filtered[2].title == "Movie B"

    def test_filter_duplicates_empty_list(self, llm_service):
        """Test filtering with empty list."""
        suggestions = []
        filtered = llm_service._filter_duplicates(suggestions)
        assert len(filtered) == 0

    def test_filter_duplicates_no_duplicates(self, llm_service):
        """Test filtering when there are no duplicates."""
        suggestions = [
            MovieSuggestion(title="Movie A", year=2018),
            MovieSuggestion(title="Movie B", year=2019),
            MovieSuggestion(title="Movie C", year=2020),
        ]

        filtered = llm_service._filter_duplicates(suggestions)

        assert len(filtered) == 3
        assert filtered == suggestions

    @pytest.mark.asyncio
    async def test_generate_movie_suggestions_filters_duplicates(self, llm_service):
        """Test that generate_movie_suggestions applies duplicate filtering."""
        # Mock the _generate_suggestions method to return duplicates
        mock_suggestions = [
            MovieSuggestion(title="The Matrix", year=1999),
            MovieSuggestion(title="The Matrix", year=1999),  # Duplicate
            MovieSuggestion(title="Inception", year=2010),
        ]

        llm_service._generate_suggestions = AsyncMock(return_value=mock_suggestions)

        result = await llm_service.generate_movie_suggestions("sci-fi movies", 10)

        # Should have filtered out the duplicate
        assert len(result) == 2
        assert result[0].title == "The Matrix"
        assert result[1].title == "Inception"

    @pytest.mark.asyncio
    async def test_generate_tv_suggestions_filters_duplicates(self, llm_service):
        """Test that generate_tv_suggestions applies duplicate filtering."""
        # Mock the _generate_suggestions method to return duplicates
        mock_suggestions = [
            TVSeriesSuggestion(title="Breaking Bad", year=2008),
            TVSeriesSuggestion(title="breaking bad", year=2008),  # Case duplicate
            TVSeriesSuggestion(title="Better Call Saul", year=2015),
        ]

        llm_service._generate_suggestions = AsyncMock(return_value=mock_suggestions)

        result = await llm_service.generate_tv_suggestions("crime dramas", 10)

        # Should have filtered out the duplicate
        assert len(result) == 2
        assert result[0].title == "Breaking Bad"
        assert result[1].title == "Better Call Saul"
