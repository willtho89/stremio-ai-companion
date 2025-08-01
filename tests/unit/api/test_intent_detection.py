"""
Unit tests for user intent detection functionality.
"""

from app.utils.parsing import detect_user_intent
from app.models.enums import ContentType


class TestIntentDetection:
    """Unit tests for the _detect_user_intent function."""

    def test_movie_intent_detection(self):
        """Test detection of movie-specific queries."""
        movie_queries = [
            "movies about friendship",
            "best films of 2023",
            "action movies",
            "romantic films",
            "blockbuster movies",
            "cinema classics",
            "feature films about war",
            "motion pictures from the 90s",
            "comedy flicks",
            "horror movie recommendations",
        ]

        for query in movie_queries:
            intent = detect_user_intent(query)
            assert intent == ContentType.MOVIE, f"Failed to detect movie intent for: '{query}'"

    def test_series_intent_detection(self):
        """Test detection of TV series-specific queries."""
        series_queries = [
            "tv shows about crime",
            "best television series",
            "drama series recommendations",
            "sitcom shows",
            "episodes of comedy",
            "seasons of thriller shows",
            "miniseries about history",
            "tv series recommendations",
            "television shows from the 80s",
            "documentary series about nature",
        ]

        for query in series_queries:
            intent = detect_user_intent(query)
            assert intent == ContentType.SERIES, f"Failed to detect series intent for: '{query}'"

    def test_ambiguous_queries(self):
        """Test queries that don't clearly indicate movies or series."""
        ambiguous_queries = [
            "sci-fi about time travel",
            "comedy recommendations",
            "action with explosions",
            "romantic stories",
            "thriller content",
            "horror recommendations",
            "drama about family",
            "mystery content",
            "adventure stories",
            "cinema and television content",  # mixed content types
            "",  # empty string
        ]

        for query in ambiguous_queries:
            intent = detect_user_intent(query)
            assert intent is None, f"Should not detect specific intent for: '{query}'"

    def test_mixed_intent_queries(self):
        """Test queries that mention both movies and series."""
        mixed_queries = [
            "movies and tv shows about sci-fi",
            "films and series recommendations",
            "movie or tv show about crime",
        ]

        for query in mixed_queries:
            intent = detect_user_intent(query)
            assert intent is None, f"Should not detect specific intent for mixed query: '{query}'"

    def test_edge_cases(self):
        """Test edge cases and special scenarios."""
        # Test None input
        assert detect_user_intent(None) is None

        # Test empty string
        assert detect_user_intent("") is None

        # Test whitespace only
        assert detect_user_intent("   ") is None

        # Test case insensitivity
        assert detect_user_intent("MOVIES ABOUT ACTION") == ContentType.MOVIE
        assert detect_user_intent("TV SHOWS ABOUT DRAMA") == ContentType.SERIES

        # Test partial word matches (should not match)
        assert detect_user_intent("moviestar biography") is None
        assert detect_user_intent("showroom design") is None

    def test_show_context_handling(self):
        """Test special handling of 'show' word in different contexts."""
        # "show" by itself should indicate series
        assert detect_user_intent("comedy show") == ContentType.SERIES
        assert detect_user_intent("talk show") == ContentType.SERIES

        # "movie show" should indicate movie (movie takes precedence)
        assert detect_user_intent("movie show") == ContentType.MOVIE
        assert detect_user_intent("film show") == ContentType.MOVIE

        # "show" in non-TV context should not indicate series
        assert detect_user_intent("show me action content") is None
        assert detect_user_intent("showdown western") is None
