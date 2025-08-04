"""
Tests for the movie-related models.
"""

import pytest
from pydantic import ValidationError

from app.models.movie import MovieSuggestions, StremioMeta, MovieSuggestion


class TestMovieSuggestions:
    """Tests for the MovieSuggestions model."""

    def test_valid_movie_suggestions(self):
        """Test creating a valid MovieSuggestions object."""
        suggestions = MovieSuggestions(
            movies=[
                MovieSuggestion(title="The Shawshank Redemption", year=1994),
                MovieSuggestion(title="The Godfather", year=1972),
                MovieSuggestion(title="The Dark Knight", year=2008),
            ]
        )

        assert len(suggestions.movies) == 3
        assert suggestions.movies[0].title == "The Shawshank Redemption"
        assert suggestions.movies[0].year == 1994
        assert suggestions.movies[1].title == "The Godfather"
        assert suggestions.movies[1].year == 1972
        assert suggestions.movies[2].title == "The Dark Knight"
        assert suggestions.movies[2].year == 2008

    def test_empty_movies_list(self):
        """Test validation for empty movies list."""
        with pytest.raises(ValidationError) as exc_info:
            MovieSuggestions(movies=[])

        assert "At least one movie suggestion is required" in str(exc_info.value)

    def test_none_movies_list(self):
        """Test validation for None movies list."""
        with pytest.raises(ValidationError) as exc_info:
            MovieSuggestions(movies=None)

        assert "Input should be a valid list" in str(exc_info.value)


class TestStremioMeta:
    """Tests for the StremioMeta model."""

    def test_valid_stremio_meta(self):
        """Test creating a valid StremioMeta object."""
        meta = StremioMeta(
            id="tmdb:550",
            type="movie",
            name="Fight Club",
            poster="https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
            background="https://image.tmdb.org/t/p/w1280/hZkgoQYus5vegHoetLkCJzb17zJ.jpg",
            description="A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression into a shocking new form of therapy.",
            releaseInfo="1999",
            imdbRating=8.4,
            genre=["Drama", "Thriller"],
            runtime="139 min",
        )

        assert meta.id == "tmdb:550"
        assert meta.type == "movie"
        assert meta.name == "Fight Club"
        assert meta.poster == "https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg"
        assert meta.background == "https://image.tmdb.org/t/p/w1280/hZkgoQYus5vegHoetLkCJzb17zJ.jpg"
        assert (
            meta.description
            == "A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression into a shocking new form of therapy."
        )
        assert meta.releaseInfo == "1999"
        assert meta.imdbRating == 8.4
        assert meta.genre == ["Drama", "Thriller"]
        assert meta.runtime == "139 min"

    def test_minimal_stremio_meta(self):
        """Test creating a minimal StremioMeta object with only required fields."""
        meta = StremioMeta(id="tmdb:123", name="Minimal Movie")

        assert meta.id == "tmdb:123"
        assert meta.type == "movie"  # Default value
        assert meta.name == "Minimal Movie"
        assert meta.poster is None
        assert meta.background is None
        assert meta.description is None
        assert meta.releaseInfo is None
        assert meta.imdbRating is None
        assert meta.genre is None
        assert meta.runtime is None

    def test_missing_required_fields(self):
        """Test validation for missing required fields."""
        with pytest.raises(ValidationError) as exc_info:
            StremioMeta(type="movie")

        assert "Field required" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            StremioMeta(id="tmdb:123")

        assert "Field required" in str(exc_info.value)

    def test_model_dump_exclude_none(self):
        """Test that model_dump with exclude_none works correctly."""
        meta = StremioMeta(id="tmdb:123", name="Test Movie")

        dumped = meta.model_dump(exclude_none=True)

        assert "id" in dumped
        assert "type" in dumped
        assert "name" in dumped
        assert "poster" not in dumped
        assert "background" not in dumped
        assert "description" not in dumped
        assert "releaseInfo" not in dumped
        assert "imdbRating" not in dumped
        assert "genre" not in dumped
        assert "runtime" not in dumped
