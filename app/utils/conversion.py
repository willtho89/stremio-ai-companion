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
    tmdb_poster = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path', '')}" if movie.get('poster_path') else None
    
    meta = StremioMeta(
        id=f"tmdb:{movie.get('id')}",
        type="movie",
        name=movie.get("title", "Unknown"),
        poster=poster_url or tmdb_poster,
        background=f"https://image.tmdb.org/t/p/w1280{movie.get('backdrop_path', '')}" if movie.get('backdrop_path') else None,
        description=movie.get("overview", ""),
        releaseInfo=movie.get("release_date", "").split("-")[0] if movie.get("release_date") else None,
        imdbRating=movie.get("vote_average"),
        genre=[genre["name"] for genre in movie.get("genres", [])] if movie.get("genres") else None,
        runtime=f"{movie.get('runtime', 0)} min" if movie.get("runtime") else None
    )
    
    return meta.model_dump(exclude_none=True)