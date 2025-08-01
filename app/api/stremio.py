"""
Stremio addon API routes for the Stremio AI Companion application.
"""

import asyncio
import json
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import logger
from app.models.config import Config
from app.services.encryption import encryption_service
from app.services.llm import LLMService
from app.services.rpdb import RPDBService
from app.services.tmdb import TMDBService
from app.utils.conversion import movie_to_stremio_meta
from app.utils.parsing import parse_movie_with_year
from core.config import settings

router = APIRouter(tags=["Stremio API"])


@router.get("/config/{config}/manifest.json")
async def get_manifest(config: str):
    """
    Return the Stremio addon manifest.

    This endpoint is called by Stremio to get information about the addon.
    """
    try:
        config_data = encryption_service.decrypt(config)
        # validate model
        Config.model_validate(json.loads(config_data))

        return {
            "id": "ai.companion.stremio",
            "version": settings.APP_VERSION,
            "name": "AI Companion",
            "description": "Your AI-powered movie discovery companion",
            "logo": "https://raw.githubusercontent.com/willtho89/stremio-ai-companion/refs/heads/main/.assets/logo2_256.png",
            "resources": ["catalog"],
            "types": ["movie"],
            "catalogs": [
                {
                    "type": "movie",
                    "id": "ai_companion_movie",
                    "name": "AI Movie Discovery",
                    "extra": [{"name": "search", "isRequired": True}],
                }
            ],
        }
    except Exception as e:
        logger.error(f"Manifest request failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid config")


async def _process_catalog_request(config: str, catalog_id: str, search: str):
    """
    Shared catalog processing logic.

    Args:
        config: Encrypted configuration string
        catalog_id: Catalog ID from Stremio
        search: Search query from Stremio

    Returns:
        Dictionary with movie metadata in Stremio format

    Raises:
        HTTPException: If processing fails
    """
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))

        logger.info(f"Processing catalog request for '{search}' with {config_obj.max_results} max results")

        llm_service = LLMService(config_obj)
        tmdb_service = TMDBService(config_obj.tmdb_read_access_token)
        rpdb_service = RPDBService(config_obj.posterdb_api_key) if config_obj.use_posterdb else None

        # Parse the search query to extract title and year
        if not search:
            search = "Give me some movies you think are must sees"

        # Extract year from search query if present
        title, search_year = parse_movie_with_year(search)

        movie_titles = await llm_service.generate_movie_suggestions(search, config_obj.max_results)
        logger.info(f"Generated {len(movie_titles)} movie suggestions: {movie_titles}")

        tasks = []
        for i, movie_title in enumerate(movie_titles):
            # Parse each movie title to extract title and year from LLM response
            title, movie_year = parse_movie_with_year(movie_title)

            # Use the year from the movie title if available, otherwise use search year for first result
            year_filter = movie_year or (search_year if (i == 0 and search_year) else None)

            tasks.append(tmdb_service.search_movie(title, year_filter, config_obj.include_adult))

        tmdb_results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Completed TMDB searches for {len(tmdb_results)} movies")

        # Get movie details for all valid results concurrently
        detail_tasks = []
        valid_results = []
        for result in tmdb_results:
            if isinstance(result, dict) and result:
                detail_tasks.append(tmdb_service.get_movie_details(result["id"]))
                valid_results.append(result)

        movie_details_list = await asyncio.gather(*detail_tasks, return_exceptions=True)

        # Collect IMDB IDs for RPDB poster fetching
        poster_tasks = []
        movie_details_with_imdb = []

        for movie_details in movie_details_list:
            if isinstance(movie_details, dict) and movie_details:
                movie_details_with_imdb.append(movie_details)
                if rpdb_service:
                    imdb_id = movie_details.get("external_ids", {}).get("imdb_id")
                    if imdb_id:
                        poster_tasks.append(rpdb_service.get_poster(imdb_id))
                    else:
                        poster_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
                else:
                    poster_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))

        # Fetch all RPDB posters concurrently
        poster_urls = await asyncio.gather(*poster_tasks, return_exceptions=True) if poster_tasks else []

        # Build final metadata
        metas = []
        for i, movie_details in enumerate(movie_details_with_imdb):
            poster_url = None
            if i < len(poster_urls) and isinstance(poster_urls[i], str):
                poster_url = poster_urls[i]

            meta = movie_to_stremio_meta(movie_details, poster_url)
            metas.append(meta)

        logger.info(f"Returning {len(metas)} movie metadata entries")
        return {"metas": metas}

    except Exception as e:
        logger.error(f"Catalog request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/{config}/catalog/movie/{catalog_id}.json")
async def get_catalog(config: str, catalog_id: str, search: Optional[str] = Query(default=None)):
    """
    Path-based catalog endpoint.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """
    return await _process_catalog_request(config, catalog_id, search)


@router.get("/config/{config}/catalog/movie/{catalog_id}/search={search}.json")
async def get_catalog_search(config: str, catalog_id: str, search: str):
    """
    Path-based catalog search endpoint.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """
    return await _process_catalog_request(config, catalog_id, search)
