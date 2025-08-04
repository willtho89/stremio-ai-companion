"""
Conversion utilities for the Stremio AI Companion application.
"""

from typing import Dict, Any, Optional

from app.models.enums import ContentType
from app.models.movie import StremioMeta


def content_to_stremio_meta(
    content_data: Dict[str, Any], content_type: ContentType, poster_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convert TMDB content data to Stremio metadata format.

    Args:
        content_data: The content data from TMDB API (movie or TV series)
        content_type: The type of content (movie or series)
        poster_url: Optional custom poster URL from RPDB

    Returns:
        A dictionary with content metadata in Stremio format
    """
    tmdb_poster = (
        f"https://image.tmdb.org/t/p/w500{content_data.get('poster_path', '')}"
        if content_data.get("poster_path")
        else None
    )

    # Handle runtime based on content type
    runtime_str = None
    if content_type == ContentType.MOVIE:
        if content_data.get("runtime"):
            runtime_str = f"{content_data.get('runtime', 0)} min"
    else:  # Series
        episode_runtime = content_data.get("episode_run_time", [])
        if episode_runtime:
            avg_runtime = sum(episode_runtime) // len(episode_runtime)
            runtime_str = f"{avg_runtime} min/ep"

    # Handle release date based on content type
    release_date_field = "release_date" if content_type == ContentType.MOVIE else "first_air_date"
    release_info = (
        content_data.get(release_date_field, "").split("-")[0] if content_data.get(release_date_field) else None
    )

    meta = StremioMeta(
        id=f"tmdb:{content_data.get('id')}",
        type=content_type.value,
        name=content_data.get("title", content_data.get("name")),
        poster=poster_url or tmdb_poster,
        background=(
            f"https://image.tmdb.org/t/p/w1280{content_data.get('backdrop_path', '')}"
            if content_data.get("backdrop_path")
            else None
        ),
        description=content_data.get("overview", ""),
        releaseInfo=release_info,
        imdbRating=content_data.get("vote_average"),
        genre=[genre["name"] for genre in content_data.get("genres", [])] if content_data.get("genres") else None,
        runtime=runtime_str,
    )

    return meta.model_dump(exclude_none=True)


def movie_to_stremio_meta(movie: Dict[str, Any], poster_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert TMDB movie data to Stremio metadata format.

    Args:
        movie: The movie data from TMDB API
        poster_url: Optional custom poster URL from RPDB

    Returns:
        A dictionary with movie metadata in Stremio format
    """
    return content_to_stremio_meta(movie, ContentType.MOVIE, poster_url)


def tv_to_stremio_meta(tv_series: Dict[str, Any], poster_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert TMDB TV series data to Stremio metadata format.

    Args:
        tv_series: The TV series data from TMDB API
        poster_url: Optional custom poster URL from RPDB

    Returns:
        A dictionary with TV series metadata in Stremio format
    """
    return content_to_stremio_meta(tv_series, ContentType.SERIES, poster_url)
