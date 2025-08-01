"""
Pytest configuration and fixtures for the Stremio AI Companion tests.
"""

import os
import sys
import pytest
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

# Add the project root directory to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from app.models.config import Config
from app.models.movie import StremioMeta, MovieSuggestions


@pytest.fixture
def sample_config() -> Config:
    """
    Fixture providing a sample Config object for testing.
    """
    return Config(
        openai_api_key="sk-test123456789012345678901234567890",
        openai_base_url="https://api.openai.com/v1",
        model_name="gpt-4.1-mini",
        tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        max_results=20,
        include_adult=False,
        use_posterdb=False,
        posterdb_api_key=None
    )


@pytest.fixture
def sample_config_with_posterdb() -> Config:
    """
    Fixture providing a sample Config object with RPDB enabled for testing.
    """
    return Config(
        openai_api_key="sk-test123456789012345678901234567890",
        openai_base_url="https://api.openai.com/v1",
        model_name="gpt-4.1-mini",
        tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        max_results=20,
        include_adult=False,
        use_posterdb=True,
        posterdb_api_key="rpdb-test1234567890"
    )


@pytest.fixture
def sample_movie_suggestions() -> MovieSuggestions:
    """
    Fixture providing a sample MovieSuggestions object for testing.
    """
    return MovieSuggestions(
        movies=[
            "The Shawshank Redemption (1994)",
            "The Godfather (1972)",
            "The Dark Knight (2008)",
            "Pulp Fiction (1994)",
            "Inception (2010)"
        ]
    )


@pytest.fixture
def sample_tmdb_movie() -> Dict[str, Any]:
    """
    Fixture providing a sample TMDB movie data for testing.
    """
    return {
        "id": 550,
        "title": "Fight Club",
        "overview": "A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression into a shocking new form of therapy.",
        "release_date": "1999-10-15",
        "poster_path": "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        "backdrop_path": "/hZkgoQYus5vegHoetLkCJzb17zJ.jpg",
        "vote_average": 8.4,
        "genres": [
            {"id": 18, "name": "Drama"},
            {"id": 53, "name": "Thriller"}
        ],
        "runtime": 139,
        "external_ids": {
            "imdb_id": "tt0137523"
        }
    }


@pytest.fixture
def sample_stremio_meta() -> StremioMeta:
    """
    Fixture providing a sample StremioMeta object for testing.
    """
    return StremioMeta(
        id="tmdb:550",
        type="movie",
        name="Fight Club",
        poster="https://image.tmdb.org/t/p/w500/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
        background="https://image.tmdb.org/t/p/w1280/hZkgoQYus5vegHoetLkCJzb17zJ.jpg",
        description="A ticking-time-bomb insomniac and a slippery soap salesman channel primal male aggression into a shocking new form of therapy.",
        releaseInfo="1999",
        imdbRating=8.4,
        genre=["Drama", "Thriller"],
        runtime="139 min"
    )