"""
Tests for the parsing utility functions.
"""

import pytest
from app.utils.parsing import parse_query_with_year, parse_movie_with_year


class TestParseQueryWithYear:
    """Tests for the parse_query_with_year function."""

    def test_with_year(self):
        """Test parsing a query with a year."""
        title, year = parse_query_with_year("twins (1988)")
        assert title == "twins"
        assert year == 1988

    def test_without_year(self):
        """Test parsing a query without a year."""
        title, year = parse_query_with_year("twins")
        assert title == "twins"
        assert year is None

    def test_with_spaces(self):
        """Test parsing a query with spaces."""
        title, year = parse_query_with_year("The Matrix (1999)")
        assert title == "The Matrix"
        assert year == 1999

    def test_with_extra_spaces(self):
        """Test parsing a query with extra spaces."""
        title, year = parse_query_with_year("  Inception  (2010)  ")
        assert title == "Inception"
        assert year == 2010

    def test_with_invalid_year_format(self):
        """Test parsing a query with an invalid year format."""
        title, year = parse_query_with_year("Star Wars (19)")
        assert title == "Star Wars (19)"
        assert year is None

    def test_with_year_not_at_end(self):
        """Test parsing a query with a year not at the end."""
        title, year = parse_query_with_year("(1977) Star Wars")
        assert title == "(1977) Star Wars"
        assert year is None


class TestParseMovieWithYear:
    """Tests for the parse_movie_with_year function."""

    def test_with_year(self):
        """Test parsing a movie title with a year."""
        title, year = parse_movie_with_year("The Matrix (1999)")
        assert title == "The Matrix"
        assert year == 1999

    def test_without_year(self):
        """Test parsing a movie title without a year."""
        title, year = parse_movie_with_year("Inception")
        assert title == "Inception"
        assert year is None

    def test_with_spaces(self):
        """Test parsing a movie title with spaces."""
        title, year = parse_movie_with_year("The Shawshank Redemption (1994)")
        assert title == "The Shawshank Redemption"
        assert year == 1994

    def test_with_extra_spaces(self):
        """Test parsing a movie title with extra spaces."""
        title, year = parse_movie_with_year("  Pulp Fiction  (1994)  ")
        assert title == "Pulp Fiction"
        assert year == 1994

    def test_with_invalid_year_format(self):
        """Test parsing a movie title with an invalid year format."""
        title, year = parse_movie_with_year("The Godfather (19)")
        assert title == "The Godfather (19)"
        assert year is None

    def test_with_year_not_at_end(self):
        """Test parsing a movie title with a year not at the end."""
        title, year = parse_movie_with_year("(1972) The Godfather")
        assert title == "(1972) The Godfather"
        assert year is None