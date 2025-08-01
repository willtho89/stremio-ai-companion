"""
TMDB service for the Stremio AI Companion application.
"""

import logging
from typing import Dict, Any, Optional

import httpx


class TMDBService:
    """
    Service for interacting with The Movie Database (TMDB) API.

    This service handles searching for movies and retrieving movie details
    from the TMDB API.
    """

    def __init__(self, read_access_token: str):
        """
        Initialize the TMDB service with an access token.

        Args:
            read_access_token: TMDB API read access token
        """
        self.read_access_token = read_access_token
        self.base_url = "https://api.themoviedb.org/3"
        self.logger = logging.getLogger("stremio_ai_companion.TMDBService")

    def _get_headers(self) -> Dict[str, str]:
        """
        Get the headers required for TMDB API requests.

        Returns:
            Dictionary of HTTP headers
        """
        return {"accept": "application/json", "Authorization": f"Bearer {self.read_access_token}"}

    async def search_movie(
        self, title: str, year: Optional[int] = None, include_adult: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a movie by title and optional year.

        Args:
            title: Movie title to search for
            year: Optional release year to filter by
            include_adult: Whether to include adult content in results

        Returns:
            Dictionary with movie data or None if not found
        """
        self.logger.debug(f"Searching TMDB for movie: '{title}'" + (f" ({year})" if year else ""))
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                params = {
                    "query": title,
                    "include_adult": "true" if include_adult else "false",
                    "language": "en-US",
                    "page": "1",
                }

                # Add year filter if provided
                if year:
                    params["primary_release_year"] = str(year)

                response = await client.get(f"{self.base_url}/search/movie", params=params, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()

                if response.status_code == 401:
                    self.logger.error("TMDB API authentication failed - check read access token")
                    return None

                if data.get("results"):
                    result = data["results"][0]
                    self.logger.debug(
                        f"Found TMDB result for '{title}': {result.get('title', 'Unknown')} ({result.get('release_date', 'Unknown')[:4] if result.get('release_date') else 'Unknown'})"
                    )
                    return result
                else:
                    self.logger.warning(f"No TMDB results found for '{title}'" + (f" ({year})" if year else ""))
                return None
            except httpx.TimeoutException:
                self.logger.warning(f"TMDB search timeout for: {title}")
                return None
            except httpx.HTTPStatusError as e:
                self.logger.error(f"TMDB HTTP error {e.response.status_code} for: {title}")
                return None
            except Exception as e:
                self.logger.error(f"TMDB search error for {title}: {e}")
                return None

    async def search_tv(
        self, title: str, year: Optional[int] = None, include_adult: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Search for a TV series by title and optional year.

        Args:
            title: TV series title to search for
            year: Optional first air date year to filter by
            include_adult: Whether to include adult content in results

        Returns:
            Dictionary with TV series data or None if not found
        """
        self.logger.debug(f"Searching TMDB for TV series: '{title}'" + (f" ({year})" if year else ""))
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                params = {
                    "query": title,
                    "include_adult": "true" if include_adult else "false",
                    "language": "en-US",
                    "page": "1",
                }

                # Add year filter if provided
                if year:
                    params["first_air_date_year"] = str(year)

                response = await client.get(f"{self.base_url}/search/tv", params=params, headers=self._get_headers())
                response.raise_for_status()
                data = response.json()

                if response.status_code == 401:
                    self.logger.error("TMDB API authentication failed - check read access token")
                    return None

                if data.get("results"):
                    result = data["results"][0]
                    self.logger.debug(
                        f"Found TMDB result for '{title}': {result.get('name', 'Unknown')} ({result.get('first_air_date', 'Unknown')[:4] if result.get('first_air_date') else 'Unknown'})"
                    )
                    return result
                else:
                    self.logger.warning(f"No TMDB results found for '{title}'" + (f" ({year})" if year else ""))
                return None
            except httpx.TimeoutException:
                self.logger.warning(f"TMDB search timeout for: {title}")
                return None
            except httpx.HTTPStatusError as e:
                self.logger.error(f"TMDB HTTP error {e.response.status_code} for: {title}")
                return None
            except Exception as e:
                self.logger.error(f"TMDB search error for {title}: {e}")
                return None

    async def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a movie by ID.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Dictionary with movie details or None if not found
        """
        self.logger.debug(f"Fetching TMDB details for movie ID: {movie_id}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                params = {"language": "en-US", "append_to_response": "external_ids"}  # This includes IMDB ID

                response = await client.get(
                    f"{self.base_url}/movie/{movie_id}", params=params, headers=self._get_headers()
                )
                response.raise_for_status()
                details = response.json()
                self.logger.debug(
                    f"Successfully fetched details for movie ID {movie_id}: {details.get('title', 'Unknown')}"
                )
                return details
            except httpx.TimeoutException:
                self.logger.warning(f"TMDB details timeout for movie ID: {movie_id}")
                return None
            except httpx.HTTPStatusError as e:
                self.logger.error(f"TMDB HTTP error {e.response.status_code} for movie ID: {movie_id}")
                return None
            except Exception as e:
                self.logger.error(f"TMDB details error for movie ID {movie_id}: {e}")
                return None

    async def get_tv_details(self, tv_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a TV series by ID.

        Args:
            tv_id: TMDB TV series ID

        Returns:
            Dictionary with TV series details or None if not found
        """
        self.logger.debug(f"Fetching TMDB details for TV series ID: {tv_id}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                params = {"language": "en-US", "append_to_response": "external_ids"}  # This includes IMDB ID

                response = await client.get(f"{self.base_url}/tv/{tv_id}", params=params, headers=self._get_headers())
                response.raise_for_status()
                details = response.json()
                self.logger.debug(
                    f"Successfully fetched details for TV series ID {tv_id}: {details.get('name', 'Unknown')}"
                )
                return details
            except httpx.TimeoutException:
                self.logger.warning(f"TMDB details timeout for TV series ID: {tv_id}")
                return None
            except httpx.HTTPStatusError as e:
                self.logger.error(f"TMDB HTTP error {e.response.status_code} for TV series ID: {tv_id}")
                return None
            except Exception as e:
                self.logger.error(f"TMDB details error for TV series ID {tv_id}: {e}")
                return None
