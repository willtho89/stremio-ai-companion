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


class TVSeriesSuggestion(BaseModel):
    """
    Individual TV series suggestion with structured fields.
    """

    title: str = Field(description="The TV series title without year")
    year: int = Field(description="The first air year of the series")


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
    imdb_id: Optional[str] = None
    type: str = "movie"
    name: str
    poster: Optional[str] = None
    background: Optional[str] = None
    logo: Optional[str] = None
    description: Optional[str] = None
    releaseInfo: Optional[str] = None
    imdbRating: Optional[str] = None
    genre: Optional[List[str]] = None
    runtime: Optional[str] = None
    behaviorHints: Optional[dict] = None

    @field_validator("imdbRating", mode="before")
    @classmethod
    def validate_imdb_rating(cls, v):
        if v is None:
            return v

        # Convert float to string with one decimal place if needed
        if isinstance(v, (int, float)):
            return f"{float(v):.1f}"

        # If it's already a string, validate format
        if isinstance(v, str):
            try:
                # Parse and reformat to ensure one decimal place
                rating = float(v)
                return f"{rating:.1f}"
            except ValueError:
                raise ValueError("imdbRating must be a valid number")

        raise ValueError("imdbRating must be a number or string representation of a number")


class StremioResponse(BaseModel):
    metas: List[StremioMeta] = Field(description="List of Stremio metadata objects", default_factory=list)
