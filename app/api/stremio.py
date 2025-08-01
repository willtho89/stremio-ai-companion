"""
Stremio addon API routes for the Stremio AI Companion application.
"""

import asyncio
import json
import re
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import logger
from app.models.config import Config
from app.services.encryption import encryption_service
from app.services.llm import LLMService
from app.services.rpdb import RPDBService
from app.services.tmdb import TMDBService
from app.utils.conversion import movie_to_stremio_meta, tv_to_stremio_meta
from app.utils.parsing import parse_movie_with_year
from app.core.config import settings

router = APIRouter(tags=["Stremio API"])


def _detect_user_intent(search: str) -> Optional[str]:
    """
    Detect user intent from search query using regex patterns.

    Args:
        search: Search query from user

    Returns:
        "movie" if user is specifically looking for movies,
        "series" if user is specifically looking for TV shows/series,
        None if intent is unclear or general
    """
    if not search:
        return None

    search_lower = search.lower()

    # Movie-specific patterns (more comprehensive)
    movie_patterns = [
        r"\bmovies?\b",  # "movie", "movies"
        r"\bfilms?\b",  # "film", "films"
        r"\bcinema\b",  # "cinema"
        r"\bflicks?\b",  # "flick", "flicks"
        r"\bmotion pictures?\b",  # "motion picture"
        r"\bfeature films?\b",  # "feature film"
        r"\bblockbusters?\b",  # "blockbuster"
    ]

    # TV/Series-specific patterns (more comprehensive)
    series_patterns = [
        r"\btv\s+shows?\b",  # "tv show", "tv shows"
        r"\btelevision\s+shows?\b",  # "television show"
        r"\btelevision\b",  # "television"
        r"\bseries\b",  # "series"
        r"\bshows?\b",  # "show", "shows" (when not preceded by movie-related words)
        r"\btv\s+series\b",  # "tv series"
        r"\btelevision\s+series\b",  # "television series"
        r"\bepisodes?\b",  # "episode", "episodes"
        r"\bseasons?\b",  # "season", "seasons"
        r"\bsitcoms?\b",  # "sitcom", "sitcoms"
        r"\bdramas?\s+series\b",  # "drama series"
        r"\bminiseries\b",  # "miniseries"
        r"\bdocumentary\s+series\b",  # "documentary series"
    ]

    # Check for movie patterns
    movie_matches = sum(1 for pattern in movie_patterns if re.search(pattern, search_lower))

    # Check for series patterns, but exclude "shows" if it's preceded by movie-related words
    series_matches = 0
    for pattern in series_patterns:
        if pattern == r"\bshows?\b":
            # Special handling for "shows" - exclude if preceded by movie words or in non-TV context
            if (
                re.search(r"\bshows?\b", search_lower)
                and not re.search(r"\b(?:movie|film|cinema)\s+shows?\b", search_lower)
                and not re.search(r"\bshow\s+me\b", search_lower)
            ):
                series_matches += 1
        else:
            if re.search(pattern, search_lower):
                series_matches += 1

    # Check for mixed content indicators
    has_mixed_content = re.search(r"\b(?:and|or)\b", search_lower) and movie_matches > 0 and series_matches > 0

    # Determine intent based on matches
    if has_mixed_content:
        return None  # Mixed content, unclear intent
    elif movie_matches > 0 and series_matches == 0:
        return "movie"
    elif series_matches > 0 and movie_matches == 0:
        return "series"
    else:
        # If both or neither are detected, intent is unclear
        return None


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

        logger.info(f"Movie metadata pipeline completed with {len(movie_metas)} results")
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

        logger.info(f"TV series metadata pipeline completed with {len(series_metas)} results")
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
            "id": "ai.companion.stremio",
            "version": settings.APP_VERSION,
            "name": "AI Companion",
            "description": "Your AI-powered movie discovery companion",
            "logo": "https://raw.githubusercontent.com/willtho89/stremio-ai-companion/refs/heads/main/.assets/logo2_256.png",
            "resources": ["catalog"],
            "types": ["movie", "series"],
            "catalogs": [
                {
                    "type": "movie",
                    "id": "ai_companion_movie",
                    "name": "AI Movie Discovery",
                    "extra": [{"name": "search", "isRequired": True}],
                },
                {
                    "type": "series",
                    "id": "ai_companion_series",
                    "name": "AI Series Discovery",
                    "extra": [{"name": "search", "isRequired": True}],
                },
            ],
        }
    except Exception as e:
        logger.error(f"Manifest request failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid config")


async def _process_catalog_request(config: str, catalog_id: str, search: str, content_type: str):
    """
    Shared catalog processing logic for both movies and TV series.

    Args:
        config: Encrypted configuration string
        catalog_id: Catalog ID from Stremio
        search: Search query from Stremio
        content_type: Type of content to return ("movie" or "series")

    Returns:
        Dictionary with movie/series metadata in Stremio format

    Raises:
        HTTPException: If processing fails
    """
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))

        logger.info(
            f"Processing {content_type} catalog request for '{search}' with {config_obj.max_results} max results"
        )

        llm_service = LLMService(config_obj)
        tmdb_service = TMDBService(config_obj.tmdb_read_access_token)
        rpdb_service = RPDBService(config_obj.posterdb_api_key) if config_obj.use_posterdb else None

        # Set default search if empty
        if not search:
            search = "Give me some great content you think are must sees"

        # Detect user intent from search query
        user_intent = _detect_user_intent(search)

        # If user intent conflicts with endpoint type, return empty list
        if user_intent and user_intent != content_type:
            logger.info(
                f"User intent '{user_intent}' conflicts with endpoint type '{content_type}', returning empty list"
            )
            return {"metas": []}

        max_results = config_obj.max_results

        # Generate suggestions based on content type
        if content_type == "movie":
            movie_titles = await llm_service.generate_movie_suggestions(search, max_results)
            logger.info(f"Generated {len(movie_titles)} movie suggestions: {movie_titles}")
            movie_metas = await _process_movie_metadata_pipeline(
                tmdb_service, rpdb_service, movie_titles, config_obj.include_adult
            )
            logger.info(f"Returning {len(movie_metas)} movie metadata entries")
            return {"metas": movie_metas}
        else:  # content_type == "series"
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


@router.get("/config/{config}/catalog/movie/{catalog_id}.json")
async def get_catalog(config: str, catalog_id: str, search: Optional[str] = Query(default=None)):
    """
    Path-based catalog endpoint.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """
    return await _process_catalog_request(config, catalog_id, search, "movie")


@router.get("/config/{config}/catalog/movie/{catalog_id}/search={search}.json")
async def get_catalog_search(config: str, catalog_id: str, search: str):
    """
    Path-based catalog search endpoint for movies.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """
    return await _process_catalog_request(config, catalog_id, search, "movie")


@router.get("/config/{config}/catalog/series/{catalog_id}.json")
async def get_series_catalog(config: str, catalog_id: str, search: Optional[str] = Query(default=None)):
    """
    Path-based catalog endpoint for TV series.

    This endpoint is called by Stremio to get TV series metadata based on a search query.
    """
    return await _process_catalog_request(config, catalog_id, search, "series")


@router.get("/config/{config}/catalog/series/{catalog_id}/search={search}.json")
async def get_series_catalog_search(config: str, catalog_id: str, search: str):
    """
    Path-based catalog search endpoint for TV series.

    This endpoint is called by Stremio to get TV series metadata based on a search query.
    """
    return await _process_catalog_request(config, catalog_id, search, "series")
