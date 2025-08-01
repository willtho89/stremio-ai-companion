"""
Movie-related models for the Stremio AI Companion application.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class MovieSuggestions(BaseModel):
    """
    Pydantic model for structured movie suggestions output from LLM.

    This model is used to parse the structured output from the OpenAI API
    when generating movie suggestions.
    """

    movies: List[str] = Field(description="List of movie titles that match the search query")

    @field_validator("movies")
    @classmethod
    def validate_movies(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one movie suggestion is required")
        return v


class StremioMeta(BaseModel):
    """
    Pydantic model for Stremio metadata format.

    This model represents the metadata format expected by Stremio
    for movie entries in the catalog.
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
