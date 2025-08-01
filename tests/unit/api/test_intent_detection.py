"""
Unit tests for user intent detection functionality.
"""

from app.api.stremio import _detect_user_intent


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
            intent = _detect_user_intent(query)
            assert intent == "movie", f"Failed to detect movie intent for: '{query}'"

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
            intent = _detect_user_intent(query)
            assert intent == "series", f"Failed to detect series intent for: '{query}'"

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
            intent = _detect_user_intent(query)
            assert intent is None, f"Should not detect specific intent for: '{query}'"

    def test_mixed_intent_queries(self):
        """Test queries that mention both movies and series."""
        mixed_queries = [
            "movies and tv shows about sci-fi",
            "films and series recommendations", 
            "movie or tv show about crime",
        ]

        for query in mixed_queries:
            intent = _detect_user_intent(query)
            assert intent is None, f"Should not detect specific intent for mixed query: '{query}'"

    def test_edge_cases(self):
        """Test edge cases and special scenarios."""
        # Test None input
        assert _detect_user_intent(None) is None

        # Test empty string
        assert _detect_user_intent("") is None

        # Test whitespace only
        assert _detect_user_intent("   ") is None

        # Test case insensitivity
        assert _detect_user_intent("MOVIES ABOUT ACTION") == "movie"
        assert _detect_user_intent("TV SHOWS ABOUT DRAMA") == "series"

        # Test partial word matches (should not match)
        assert _detect_user_intent("moviestar biography") is None
        assert _detect_user_intent("showroom design") is None

    def test_show_context_handling(self):
        """Test special handling of 'show' word in different contexts."""
        # "show" by itself should indicate series
        assert _detect_user_intent("comedy show") == "series"
        assert _detect_user_intent("talk show") == "series"

        # "movie show" should indicate movie (movie takes precedence)
        assert _detect_user_intent("movie show") == "movie"
        assert _detect_user_intent("film show") == "movie"

        # "show" in non-TV context should not indicate series
        assert _detect_user_intent("show me action content") is None
        assert _detect_user_intent("showdown western") is None
