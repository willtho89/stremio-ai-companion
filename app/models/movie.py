"""
Movie and TV series related models for the Stremio AI Companion application.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MovieSuggestion(BaseModel):
    """
    Individual movie suggestion with structured fields.
    """

    title: str = Field(description="The movie title without year")
    year: int = Field(description="The release year of the movie")
    streaming_platform: Optional[str] = Field(
        default=None, description="Primary streaming platform if known (e.g., Netflix, Prime Video, Hulu)"
    )
    note: Optional[str] = Field(default=None, description="Additional context like 'New this week' or 'Trending'")


class TVSeriesSuggestion(BaseModel):
    """
    Individual TV series suggestion with structured fields.
    """

    title: str = Field(description="The TV series title without year")
    year: int = Field(description="The first air year of the series")
    streaming_platform: Optional[str] = Field(
        default=None, description="Primary streaming platform if known (e.g., Netflix, Prime Video, Hulu)"
    )
    note: Optional[str] = Field(default=None, description="Additional context like 'New season' or 'Limited series'")


class MovieSuggestions(BaseModel):
    """
    Pydantic model for structured movie suggestions output from LLM.

    This model is used to parse the structured output from the OpenAI API
    when generating movie suggestions.
    """

    movies: List[MovieSuggestion] = Field(description="List of movie suggestions with title and year")

    @field_validator("movies")
    @classmethod
    def validate_movies(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one movie suggestion is required")
        return v


class TVSeriesSuggestions(BaseModel):
    """
    Pydantic model for structured TV series suggestions output from LLM.

    This model is used to parse the structured output from the OpenAI API
    when generating TV series suggestions.
    """

    series: List[TVSeriesSuggestion] = Field(description="List of TV series suggestions with title and year")

    @field_validator("series")
    @classmethod
    def validate_series(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one TV series suggestion is required")
        return v


class StremioMeta(BaseModel):
    """
    Pydantic model for Stremio metadata format.

    This model represents the metadata format expected by Stremio
    for movie and TV series entries in the catalog.
    """

    id: str
    type: str = "movie"
    name: str
    poster: Optional[str] = None
    background: Optional[str] = None
    description: Optional[str] = None
    releaseInfo: Optional[str] = None
    imdbRating: Optional[float] = None
    genre: Optional[List[str]] = None
    runtime: Optional[str] = None
