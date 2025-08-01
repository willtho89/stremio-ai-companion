"""
Parsing utilities for the Stremio AI Companion application.
"""

import re
from typing import Tuple, Optional

from app.models.enums import ContentType


def parse_movie_with_year(movie_title: str) -> Tuple[str, Optional[int]]:
    """
    Parse a movie title from LLM response to extract title and year.

    Args:
        movie_title: The movie title string, possibly with year in parentheses

    Returns:
        A tuple containing the movie title and optional year

    Examples:
        - "The Matrix (1999)" -> ("The Matrix", 1999)
        - "Inception (2010)" -> ("Inception", 2010)
        - "Some Movie" -> ("Some Movie", None)
    """
    # Pattern to match year in parentheses
    year_pattern = r"\s*\((\d{4})\)\s*$"
    match = re.search(year_pattern, movie_title)

    if match:
        year = int(match.group(1))
        title = re.sub(year_pattern, "", movie_title).strip()
        return title, year

    return movie_title.strip(), None


def detect_user_intent(search: str) -> Optional[str]:
    """
    Detect user intent from search query using regex patterns.

    Args:
        search: Search query from user

    Returns:
        "movie" if user is specifically looking for movies,
        "series" if user is specifically looking for TV shows/series,
        None if intent is unclear or general
    """
    if not search:
        return None

    search_lower = search.lower()

    # Movie-specific patterns (more comprehensive)
    movie_patterns = [
        r"\bmovies?\b",  # "movie", "movies"
        r"\bfilms?\b",  # "film", "films"
        r"\bcinema\b",  # "cinema"
        r"\bflicks?\b",  # "flick", "flicks"
        r"\bmotion pictures?\b",  # "motion picture"
        r"\bfeature films?\b",  # "feature film"
        r"\bblockbusters?\b",  # "blockbuster"
    ]

    # TV/Series-specific patterns (more comprehensive)
    series_patterns = [
        r"\btv\s+shows?\b",  # "tv show", "tv shows"
        r"\btelevision\s+shows?\b",  # "television show"
        r"\btelevision\b",  # "television"
        r"\bseries\b",  # "series"
        r"\bshows?\b",  # "show", "shows" (when not preceded by movie-related words)
        r"\btv\s+series\b",  # "tv series"
        r"\btelevision\s+series\b",  # "television series"
        r"\bepisodes?\b",  # "episode", "episodes"
        r"\bseasons?\b",  # "season", "seasons"
        r"\bsitcoms?\b",  # "sitcom", "sitcoms"
        r"\bdramas?\s+series\b",  # "drama series"
        r"\bminiseries\b",  # "miniseries"
        r"\bdocumentary\s+series\b",  # "documentary series"
    ]

    # Check for movie patterns
    movie_matches = sum(1 for pattern in movie_patterns if re.search(pattern, search_lower))

    # Check for series patterns, but exclude "shows" if it's preceded by movie-related words
    series_matches = 0
    for pattern in series_patterns:
        if pattern == r"\bshows?\b":
            # Special handling for "shows" - exclude if preceded by movie words or in non-TV context
            if (
                re.search(r"\bshows?\b", search_lower)
                and not re.search(r"\b(?:movie|film|cinema)\s+shows?\b", search_lower)
                and not re.search(r"\bshow\s+me\b", search_lower)
            ):
                series_matches += 1
        else:
            if re.search(pattern, search_lower):
                series_matches += 1

    # Check for mixed content indicators
    has_mixed_content = re.search(r"\b(?:and|or)\b", search_lower) and movie_matches > 0 and series_matches > 0

    # Determine intent based on matches
    if has_mixed_content:
        return None  # Mixed content, unclear intent
    elif movie_matches > 0 and series_matches == 0:
        return ContentType.MOVIE
    elif series_matches > 0 and movie_matches == 0:
        return ContentType.SERIES
    else:
        # If both or neither are detected, intent is unclear
        return None
