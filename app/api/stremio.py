"""
Stremio addon API routes for the Stremio AI Companion application.
"""

import asyncio
import json
import time
from functools import lru_cache, wraps

from fastapi import APIRouter, HTTPException

from app.core.logging import logger
from app.models.config import Config
from app.services.encryption import encryption_service
from app.services.llm import LLMService
from app.services.rpdb import RPDBService
from app.services.tmdb import TMDBService
from app.utils.conversion import movie_to_stremio_meta, tv_to_stremio_meta
from app.utils.parsing import parse_movie_with_year
from app.core.config import settings
from app.models.enums import ContentType
from app.utils.parsing import detect_user_intent

router = APIRouter(tags=["Stremio API"])


def timed_lru_cache(seconds: int, maxsize: int = 128):
    """
    Decorator that creates an LRU cache with a time-based expiration.

    Args:
        seconds: Number of seconds to keep the cache valid
        maxsize: Maximum size of the LRU cache

    Returns:
        Decorated function with time-based cache expiration
    """

    def wrapper_cache(func):
        func = lru_cache(maxsize=maxsize)(func)
        func.lifetime = seconds
        func.expiration = time.time() + seconds

        @wraps(func)
        def wrapped_func(*args, **kwargs):
            if time.time() > func.expiration:
                func.cache_clear()
                func.expiration = time.time() + func.lifetime
            return func(*args, **kwargs)

        return wrapped_func

    return wrapper_cache


async def _process_movie_metadata_pipeline(tmdb_service, rpdb_service, movie_titles: list, include_adult: bool):
    """Process movie metadata pipeline that runs independently after LLM suggestions."""
    try:
        # Step 1: Search TMDB for all movies in parallel
        search_tasks = []
        for movie_title in movie_titles:
            title, movie_year = parse_movie_with_year(movie_title)
            search_tasks.append(tmdb_service.search_movie(title, movie_year, include_adult))

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        logger.info(f"Completed {len(search_results)} TMDB movie searches")

        # Step 2: Get movie details for valid results in parallel
        detail_tasks = []
        valid_search_results = []
        for result in search_results:
            if isinstance(result, dict) and result:
                detail_tasks.append(tmdb_service.get_movie_details(result["id"]))
                valid_search_results.append(result)

        detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
        logger.info(f"Completed {len(detail_results)} movie detail fetches")

        # Step 3: Get poster URLs in parallel
        poster_tasks = []
        valid_details = []
        for detail in detail_results:
            if isinstance(detail, dict) and detail:
                valid_details.append(detail)
                if rpdb_service:
                    imdb_id = detail.get("external_ids", {}).get("imdb_id")
                    if imdb_id:
                        poster_tasks.append(rpdb_service.get_poster(imdb_id))
                    else:
                        poster_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
                else:
                    poster_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))

        poster_results = await asyncio.gather(*poster_tasks, return_exceptions=True) if poster_tasks else []

        # Step 4: Build final metadata
        movie_metas = []
        for i, movie_details in enumerate(valid_details):
            poster_url = None
            if i < len(poster_results) and isinstance(poster_results[i], str):
                poster_url = poster_results[i]

            meta = movie_to_stremio_meta(movie_details, poster_url)
            movie_metas.append(meta)

        logger.debug(f"Movie metadata pipeline completed with {len(movie_metas)} results")
        return movie_metas

    except Exception as e:
        logger.error(f"Movie metadata pipeline failed: {e}")
        return []


async def _process_series_metadata_pipeline(tmdb_service, rpdb_service, series_titles: list, include_adult: bool):
    """Process TV series metadata pipeline that runs independently after LLM suggestions."""
    try:
        # Step 1: Search TMDB for all series in parallel
        search_tasks = []
        for series_title in series_titles:
            title, series_year = parse_movie_with_year(series_title)
            search_tasks.append(tmdb_service.search_tv(title, series_year, include_adult))

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        logger.info(f"Completed {len(search_results)} TMDB TV series searches")

        # Step 2: Get series details for valid results in parallel
        detail_tasks = []
        valid_search_results = []
        for result in search_results:
            if isinstance(result, dict) and result:
                detail_tasks.append(tmdb_service.get_tv_details(result["id"]))
                valid_search_results.append(result)

        detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
        logger.info(f"Completed {len(detail_results)} TV series detail fetches")

        # Step 3: Get poster URLs in parallel
        poster_tasks = []
        valid_details = []
        for detail in detail_results:
            if isinstance(detail, dict) and detail:
                valid_details.append(detail)
                if rpdb_service:
                    imdb_id = detail.get("external_ids", {}).get("imdb_id")
                    if imdb_id:
                        poster_tasks.append(rpdb_service.get_poster(imdb_id))
                    else:
                        poster_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
                else:
                    poster_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))

        poster_results = await asyncio.gather(*poster_tasks, return_exceptions=True) if poster_tasks else []

        # Step 4: Build final metadata
        series_metas = []
        for i, series_details in enumerate(valid_details):
            poster_url = None
            if i < len(poster_results) and isinstance(poster_results[i], str):
                poster_url = poster_results[i]

            meta = tv_to_stremio_meta(series_details, poster_url)
            series_metas.append(meta)

        logger.debug(f"TV series metadata pipeline completed with {len(series_metas)} results")
        return series_metas

    except Exception as e:
        logger.error(f"TV series metadata pipeline failed: {e}")
        return []


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
            "id": settings.STREMIO_ADDON_ID,
            "version": settings.APP_VERSION,
            "name": "AI Companion",
            "description": "Your AI-powered movie discovery companion",
            "logo": "https://raw.githubusercontent.com/willtho89/stremio-ai-companion/refs/heads/main/.assets/logo2_256.png",
            "resources": ["catalog"],
            "types": ["movie", "series"],
            "catalogs": [
                {
                    "type": "movie",
                    "id": settings.STREMIO_ADDON_ID.replace(".", "_") + "_movie",
                    "name": "AI Movie Discovery",
                    "extra": [{"name": "search", "isRequired": True}],
                },
                {
                    "type": "series",
                    "id": settings.STREMIO_ADDON_ID.replace(".", "_") + "_series",
                    "name": "AI Series Discovery",
                    "extra": [{"name": "search", "isRequired": True}],
                },
            ],
        }
    except Exception as e:
        logger.error(f"Manifest request failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid config")


async def _process_catalog_request(config: str, search: str, content_type: ContentType, max_results: int | None = None):
    """
    Shared catalog processing logic for both movies and TV series.

    Args:
        config: Encrypted configuration string
        search: Search query from Stremio
        content_type: Type of content to return (ContentType.MOVIE or ContentType.SERIES)

    Returns:
        Dictionary with movie/series metadata in Stremio format

    Raises:
        HTTPException: If processing fails
    """
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))

        if not max_results:
            max_results = config_obj.max_results

        logger.info(f"Processing {content_type} catalog request for '{search}' with {max_results} max results")

        llm_service = LLMService(config_obj)
        tmdb_service = TMDBService(config_obj.tmdb_read_access_token)
        rpdb_service = RPDBService(config_obj.posterdb_api_key) if config_obj.use_posterdb else None

        # Detect user intent from search query
        user_intent = detect_user_intent(search)

        # If user intent conflicts with endpoint type, return empty list
        if user_intent and user_intent != content_type:
            logger.info(
                f"User intent '{user_intent}' conflicts with endpoint type '{content_type}', returning empty list"
            )
            return {"metas": []}

        # Generate suggestions based on content type
        if content_type == ContentType.MOVIE:
            movie_titles = await llm_service.generate_movie_suggestions(search, max_results)
            logger.info(f"Generated {len(movie_titles)} movie suggestions: {movie_titles}")
            movie_metas = await _process_movie_metadata_pipeline(
                tmdb_service, rpdb_service, movie_titles, config_obj.include_adult
            )
            logger.info(f"Returning {len(movie_metas)} movie metadata entries")
            return {"metas": movie_metas}
        else:  # content_type == ContentType.SERIES
            series_titles = await llm_service.generate_tv_suggestions(search, max_results)
            logger.info(f"Generated {len(series_titles)} TV series suggestions: {series_titles}")
            series_metas = await _process_series_metadata_pipeline(
                tmdb_service, rpdb_service, series_titles, config_obj.include_adult
            )
            logger.info(f"Returning {len(series_metas)} series metadata entries")
            return {"metas": series_metas}

    except Exception as e:
        logger.error(f"Catalog request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@timed_lru_cache(seconds=14400)  # 4 hours
async def _cached_catalog(config: str, content_type: ContentType):
    """
    Cached version of the catalogue view.
    """

    # NOTE caching does not work too well in a uvicorn setting with multiple workers…
    return await _process_catalog_request(
        config,
        "Give me your current must watches which are available to stream right now",
        content_type,
        max_results=100,
    )


@router.get("/config/{config}/catalog/{content_type}/{catalog_id}.json")
async def get_catalog(config: str, content_type: ContentType, catalog_id: str):
    """
    Path-based catalog endpoint.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """

    return await _cached_catalog(config, content_type)


@router.get("/config/{config}/catalog/{content_type}/{catalog_id}/search={search}.json")
async def get_catalog_search(config: str, content_type: ContentType, catalog_id: str, search: str):
    """
    Path-based catalog search endpoint for movies.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """
    # Always use the non-cached version for explicit searches
    return await _process_catalog_request(config, search, content_type)
