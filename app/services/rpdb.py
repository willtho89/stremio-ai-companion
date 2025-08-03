"""
RatingPosterDB service for the Stremio AI Companion application.
"""

import logging
from typing import Optional


class RPDBService:
    """
    Service for interacting with the RatingPosterDB (RPDB) API.

    This service handles fetching movie posters from the RPDB API
    based on IMDB IDs.
    """

    def __init__(self, api_key: str):
        """
        Initialize the RPDB service with an API key.

        Args:
            api_key: RPDB API key
        """
        self.api_key = api_key
        self.logger = logging.getLogger("stremio_ai_companion.RPDBService")

    async def get_poster(self, imdb_id: str) -> Optional[str]:
        """
        Get a poster URL for a movie by IMDB ID.

        Args:
            imdb_id: IMDB ID of the movie

        Returns:
            URL to the poster image or None if not available
        """
        if not self.api_key or not imdb_id:
            self.logger.debug("RPDB API key or IMDB ID not provided")
            return None

        try:
            # RPDB uses direct image URLs with the API key
            # Format: https://api.ratingposterdb.com/{api_key}/imdb/poster-default/{imdb_id}.jpg
            # Ensure IMDB ID has 'tt' prefix
            if not imdb_id.startswith("tt"):
                imdb_id = f"tt{imdb_id}"

            poster_url = f"https://api.ratingposterdb.com/{self.api_key}/imdb/poster-default/{imdb_id}.jpg"

            # For valid API keys, we can return the URL directly without testing
            # The image will load if it exists, or show broken image if not
            self.logger.debug(f"Generated RPDB poster URL for {imdb_id}")
            return poster_url

        except Exception as e:
            self.logger.error(f"RPDB error for IMDB ID {imdb_id}: {e}")
            return None
