"""
Conversion utilities for the Stremio AI Companion application.
"""

from typing import Dict, Any, Optional

from app.models.movie import StremioMeta


def movie_to_stremio_meta(movie: Dict[str, Any], poster_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert TMDB movie data to Stremio metadata format.

    Args:
        movie: The movie data from TMDB API
        poster_url: Optional custom poster URL from RPDB

    Returns:
        A dictionary with movie metadata in Stremio format
    """
    tmdb_poster = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path', '')}" if movie.get("poster_path") else None

    meta = StremioMeta(
        id=f"tmdb:{movie.get('id')}",
        type="movie",
        name=movie.get("title", "Unknown"),
        poster=poster_url or tmdb_poster,
        background=(
            f"https://image.tmdb.org/t/p/w1280{movie.get('backdrop_path', '')}" if movie.get("backdrop_path") else None
        ),
        description=movie.get("overview", ""),
        releaseInfo=movie.get("release_date", "").split("-")[0] if movie.get("release_date") else None,
        imdbRating=movie.get("vote_average"),
        genre=[genre["name"] for genre in movie.get("genres", [])] if movie.get("genres") else None,
        runtime=f"{movie.get('runtime', 0)} min" if movie.get("runtime") else None,
    )

    return meta.model_dump(exclude_none=True)


def tv_to_stremio_meta(tv_series: Dict[str, Any], poster_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Convert TMDB TV series data to Stremio metadata format.

    Args:
        tv_series: The TV series data from TMDB API
        poster_url: Optional custom poster URL from RPDB

    Returns:
        A dictionary with TV series metadata in Stremio format
    """
    tmdb_poster = (
        f"https://image.tmdb.org/t/p/w500{tv_series.get('poster_path', '')}" if tv_series.get("poster_path") else None
    )

    # Calculate runtime from episode runtime
    episode_runtime = tv_series.get("episode_run_time", [])
    runtime_str = None
    if episode_runtime:
        avg_runtime = sum(episode_runtime) // len(episode_runtime)
        runtime_str = f"{avg_runtime} min/ep"

    meta = StremioMeta(
        id=f"tmdb:{tv_series.get('id')}",
        type="series",
        name=tv_series.get("name", "Unknown"),
        poster=poster_url or tmdb_poster,
        background=(
            f"https://image.tmdb.org/t/p/w1280{tv_series.get('backdrop_path', '')}"
            if tv_series.get("backdrop_path")
            else None
        ),
        description=tv_series.get("overview", ""),
        releaseInfo=tv_series.get("first_air_date", "").split("-")[0] if tv_series.get("first_air_date") else None,
        imdbRating=tv_series.get("vote_average"),
        genre=[genre["name"] for genre in tv_series.get("genres", [])] if tv_series.get("genres") else None,
        runtime=runtime_str,
    )

    return meta.model_dump(exclude_none=True)
