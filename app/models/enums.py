from enum import Enum


class ContentType(str, Enum):
    """Enum for content types supported by Stremio."""

    MOVIE = "movie"
    SERIES = "series"


class CatalogId(str, Enum):
    """Predefined catalog identifiers."""

    TRENDING = "trending"


class LLMProvider(str, Enum):
    OPENROUTER = "https://openrouter.ai/api/v1"
    OPENAI = "https://api.openai.com/v1"
    ANTHROPIC = "https://api.anthropic.com/v1"
    GEMINI = "https://generativelanguage.googleapis.com/v1beta/openai/"
