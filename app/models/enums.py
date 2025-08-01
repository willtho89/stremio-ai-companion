from enum import Enum


class ContentType(str, Enum):
    """Enum for content types supported by Stremio."""

    MOVIE = "movie"
    SERIES = "series"
