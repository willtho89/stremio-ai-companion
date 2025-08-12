"""
TMDB service for the Stremio AI Companion application.
"""

import logging
from typing import Any, Optional

import httpx
from pydantic import BaseModel, ConfigDict


class TMDBSearchParams(BaseModel):
    """Parameters for TMDB search requests."""

    model_config = ConfigDict(frozen=True)

    query: str
    language: str
    page: int = 1
    year: Optional[int] = None


class TMDBMovieSearchParams(TMDBSearchParams):
    """Parameters specific to movie search requests."""

    @property
    def api_params(self) -> dict[str, str]:
        """Convert to API parameters dictionary."""
        params = {
            "query": self.query,
            "include_adult": "false",
            "language": self.language,
            "page": str(self.page),
        }
        if self.year:
            params["primary_release_year"] = str(self.year)
        return params


class TMDBTVSearchParams(TMDBSearchParams):
    """Parameters specific to TV search requests."""

    @property
    def api_params(self) -> dict[str, str]:
        """Convert to API parameters dictionary."""
        params = {
            "query": self.query,
            "include_adult": "false",
            "language": self.language,
            "page": str(self.page),
        }
        if self.year:
            params["first_air_date_year"] = str(self.year)
        return params


class TMDBDetailsParams(BaseModel):
    """Parameters for TMDB details requests."""

    model_config = ConfigDict(frozen=True)

    language: str
    append_to_response: str = "external_ids"

    @property
    def api_params(self) -> dict[str, str]:
        """Convert to API parameters dictionary."""
        return {
            "language": self.language,
            "append_to_response": self.append_to_response,
        }


class TMDBService:
    """
    Service for interacting with The Movie Database (TMDB) API.

    This service handles searching for movies and retrieving movie details
    from the TMDB API.
    """

    def __init__(self, read_access_token: str, language: str, timeout: float = 10.0) -> None:
        """
        Initialize the TMDB service with an access token.

        Args:
            read_access_token: TMDB API read access token
            language: Language code for API requests
            timeout: HTTP request timeout in seconds
        """
        self.read_access_token = read_access_token
        self.base_url = "https://api.themoviedb.org/3"
        self.timeout = timeout
        self.logger = logging.getLogger("stremio_ai_companion.TMDBService")
        self.language = language

    @property
    def _headers(self) -> dict[str, str]:
        """
        Get the headers required for TMDB API requests.

        Returns:
            Dictionary of HTTP headers
        """
        return {"accept": "application/json", "Authorization": f"Bearer {self.read_access_token}"}

    async def _make_request(self, endpoint: str, params: dict[str, str]) -> Optional[dict[str, Any]]:
        """
        Make an HTTP request to the TMDB API.

        Args:
            endpoint: API endpoint to call
            params: Query parameters

        Returns:
            Response data or None if request failed
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(f"{self.base_url}/{endpoint}", params=params, headers=self._headers)
                response.raise_for_status()

                if response.status_code == 401:
                    self.logger.error("TMDB API authentication failed - check read access token")
                    return None

                return response.json()

            except httpx.TimeoutException:
                self.logger.warning(f"TMDB request timeout for endpoint: {endpoint}")
                return None
            except httpx.HTTPStatusError as e:
                self.logger.error(f"TMDB HTTP error {e.response.status_code} for endpoint: {endpoint}")
                return None
            except Exception as e:
                self.logger.error(f"TMDB request error for {endpoint}: {e}")
                return None

    async def search_movie(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Search for a movie by title and optional year.

        Args:
            title: Movie title to search for
            year: Optional release year to filter by

        Returns:
            Dictionary with movie data or None if not found
        """
        self.logger.debug(f"Searching TMDB for movie: '{title}'" + (f" ({year})" if year else ""))

        search_params = TMDBMovieSearchParams(query=title, year=year, language=self.language)

        data = await self._make_request("search/movie", search_params.api_params)

        if not data or not data.get("results"):
            self.logger.warning(f"No TMDB results found for movie '{title}'" + (f" ({year})" if year else ""))
            return None

        result = data["results"][0]
        self.logger.debug(
            f"Found TMDB result for '{title}': {result.get('title', 'Unknown')} "
            f"({result.get('release_date', 'Unknown')[:4] if result.get('release_date') else 'Unknown'})"
        )
        return result

    async def search_tv(
        self,
        title: str,
        year: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Search for a TV series by title and optional year.

        Args:
            title: TV series title to search for
            year: Optional first air date year to filter by

        Returns:
            Dictionary with TV series data or None if not found
        """
        self.logger.debug(f"Searching TMDB for TV series: '{title}'" + (f" ({year})" if year else ""))

        search_params = TMDBTVSearchParams(query=title, year=year, language=self.language)

        data = await self._make_request("search/tv", search_params.api_params)

        if not data or not data.get("results"):
            self.logger.warning(f"No TMDB results found for series '{title}'" + (f" ({year})" if year else ""))
            return None

        result = data["results"][0]
        self.logger.debug(
            f"Found TMDB result for '{title}': {result.get('name', 'Unknown')} "
            f"({result.get('first_air_date', 'Unknown')[:4] if result.get('first_air_date') else 'Unknown'})"
        )
        return result

    async def get_movie_details(self, movie_id: int) -> Optional[dict[str, Any]]:
        """
        Get detailed information about a movie by ID.

        Args:
            movie_id: TMDB movie ID

        Returns:
            Dictionary with movie details or None if not found
        """
        self.logger.debug(f"Fetching TMDB details for movie ID: {movie_id}")

        details_params = TMDBDetailsParams(language=self.language)
        data = await self._make_request(f"movie/{movie_id}", details_params.api_params)

        if data:
            self.logger.debug(f"Successfully fetched details for movie ID {movie_id}: {data.get('title', 'Unknown')}")

        return data

    async def get_tv_details(self, tv_id: int) -> Optional[dict[str, Any]]:
        """
        Get detailed information about a TV series by ID.

        Args:
            tv_id: TMDB TV series ID

        Returns:
            Dictionary with TV series details or None if not found
        """
        self.logger.debug(f"Fetching TMDB details for TV series ID: {tv_id}")

        details_params = TMDBDetailsParams(language=self.language)
        data = await self._make_request(f"tv/{tv_id}", details_params.api_params)

        if data:
            self.logger.debug(f"Successfully fetched details for TV series ID {tv_id}: {data.get('name', 'Unknown')}")

        return data
