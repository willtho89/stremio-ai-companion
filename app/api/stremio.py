"""
Stremio addon API routes for the Stremio AI Companion application.
"""

import asyncio
import json
import time
from functools import lru_cache, wraps
from typing import Optional, List, Union

from fastapi import APIRouter, HTTPException
from slugify import slugify

from app.core.config import settings
from app.core.logging import logger
from app.models.config import Config
from app.models.enums import ContentType
from app.models.movie import MovieSuggestion, TVSeriesSuggestion, StremioResponse
from app.services import CATALOG_PROMPTS
from app.services.cache import CACHE_INSTANCE
from app.services.encryption import encryption_service
from app.services.llm import LLMService
from app.services.rpdb import RPDBService
from app.services.tmdb import TMDBService
from app.utils.conversion import movie_to_stremio_meta, tv_to_stremio_meta
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


async def _apply_rpdb_posters(metas: List[dict], rpdb_service: Optional[RPDBService]) -> List[dict]:
    """
    Apply RPDB posters to metadata if RPDB service is available.
    This modifies the poster URLs before delivery to the user.
    """
    if not rpdb_service or not metas:
        return metas

    # Extract IMDB IDs and get RPDB posters (no longer async)
    for meta in metas:
        imdb_id = meta.get("imdb_id")
        if imdb_id:
            poster_url = rpdb_service.get_poster(imdb_id)
            if poster_url:
                meta["poster"] = poster_url

    return metas


async def _process_metadata_pipeline(
    tmdb_service,
    rpdb_service,
    suggestions: List[Union[MovieSuggestion, TVSeriesSuggestion]],
    include_adult: bool,
    *,
    search_fn,
    details_fn,
    meta_builder,
):
    """Generic metadata pipeline that runs after LLM suggestions."""
    try:
        search_tasks = []
        for suggestion in suggestions:
            search_tasks.append(search_fn(suggestion.title, suggestion.year, include_adult))

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)
        logger.debug(f"Completed {len(search_results)} TMDB searches")

        detail_tasks = []
        valid_search_results = []
        for result in search_results:
            if isinstance(result, dict) and result:
                detail_tasks.append(details_fn(result["id"]))
                valid_search_results.append(result)

        detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
        logger.debug(f"Completed {len(detail_results)} detail fetches")

        # Cache with TMDB posters only - no RPDB poster fetching here
        metas = []
        for details in detail_results:
            if isinstance(details, dict) and details:
                # Always use TMDB poster for caching (poster_url=None)
                meta = meta_builder(details, poster_url=None)
                metas.append(meta)

        logger.debug(f"Metadata pipeline completed with {len(metas)} results")
        return metas

    except Exception as e:
        logger.error(f"Metadata pipeline failed: {e}")
        return []


def build_manifest(
    types: Optional[List[str]] = None,
    include_catalogs_movies: Optional[list[str]] = None,
    include_catalogs_series: Optional[list[str]] = None,
    *,
    changed_catalogs: bool = False,
) -> dict:
    """
    Build a Stremio manifest with specified content types.

    Args:
        types: List of content types to include ("movie", "series").
               If None, includes both types.

    Returns:
        Dictionary containing the Stremio manifest
    """
    if types is None:
        types = ["movie", "series"]

    # Determine addon ID and name based on types
    if len(types) == 1:
        if types[0] == "movie":
            addon_id = f"{settings.STREMIO_ADDON_ID}-movie"
            name = "AI Movie Companion"
            description = "Your AI-powered movie discovery companion"
        else:  # series
            addon_id = f"{settings.STREMIO_ADDON_ID}-series"
            name = "AI Series Companion"
            description = "Your AI-powered series discovery companion"
    else:
        addon_id = settings.STREMIO_ADDON_ID
        name = "AI Companion"
        description = "Your AI-powered movie discovery companion"

    # Build catalogs for specified types using predefined prompts, plus optional feed catalogs
    catalogs = []
    for content_type in types:
        if content_type == "movie":
            catalogs.append(
                {
                    "type": "movie",
                    "id": settings.STREMIO_ADDON_ID.replace(".", "_") + "_movie",
                    "name": "AI Movie Discovery",
                    "extra": [{"name": "search", "isRequired": True}],
                }
            )
            if settings.ENABLE_FEED_CATALOGS and (
                changed_catalogs and include_catalogs_movies is not None or not changed_catalogs
            ):
                allowed = set(include_catalogs_movies) if changed_catalogs else set(CATALOG_PROMPTS.keys())
                for cid, cfg in CATALOG_PROMPTS.items():
                    if cid in allowed:
                        catalogs.append(
                            {
                                "type": "movie",
                                "id": f"{cid}_movie",
                                "name": cfg["title"],
                            }
                        )
        elif content_type == "series":
            catalogs.append(
                {
                    "type": "series",
                    "id": settings.STREMIO_ADDON_ID.replace(".", "_") + "_series",
                    "name": "AI Series Discovery",
                    "extra": [{"name": "search", "isRequired": True}],
                }
            )
            if settings.ENABLE_FEED_CATALOGS and (
                changed_catalogs and include_catalogs_series is not None or not changed_catalogs
            ):
                allowed = set(include_catalogs_series) if changed_catalogs else set(CATALOG_PROMPTS.keys())
                for cid, cfg in CATALOG_PROMPTS.items():
                    if cid in allowed:
                        catalogs.append(
                            {
                                "type": "series",
                                "id": f"{cid}_series",
                                "name": cfg["title"],
                            }
                        )

    return {
        "id": addon_id,
        "version": settings.APP_VERSION,
        "name": name,
        "description": description,
        "logo": "https://raw.githubusercontent.com/willtho89/stremio-ai-companion/refs/heads/main/.assets/logo2_256.png",
        "background": "https://raw.githubusercontent.com/willtho89/stremio-ai-companion/refs/heads/main/.assets/background.png",
        "resources": ["catalog"],
        "types": types,
        "catalogs": catalogs,
    }


@router.get("/config/{config}/adult/{adult}/manifest.json")
async def get_manifest(config: str, adult: int):
    """
    Return the Stremio addon manifest for combined movies and series.

    This endpoint is called by Stremio to get information about the addon.
    """
    try:
        config_data = encryption_service.decrypt(config)
        # validate model
        Config.model_validate(json.loads(config_data))

        config_obj = Config.model_validate(json.loads(config_data))
        return build_manifest(
            None,
            config_obj.include_catalogs_movies,
            config_obj.include_catalogs_series,
            changed_catalogs=config_obj.changed_catalogs,
        )
    except Exception as e:
        logger.error(f"Manifest request failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid config")


@router.get("/config/{config}/adult/{adult}/movie/manifest.json")
async def get_movie_manifest(config: str, adult: int):
    """
    Return the Stremio addon manifest for movies only.
    """
    try:
        config_data = encryption_service.decrypt(config)
        # validate model
        Config.model_validate(json.loads(config_data))

        config_obj = Config.model_validate(json.loads(config_data))
        return build_manifest(
            ["movie"], config_obj.include_catalogs_movies, None, changed_catalogs=config_obj.changed_catalogs
        )
    except Exception as e:
        logger.error(f"Movie manifest request failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid config")


@router.get("/config/{config}/adult/{adult}/series/manifest.json")
async def get_series_manifest(config: str, adult: int):
    """
    Return the Stremio addon manifest for series only.
    """
    try:
        config_data = encryption_service.decrypt(config)
        # validate model
        Config.model_validate(json.loads(config_data))

        config_obj = Config.model_validate(json.loads(config_data))
        return build_manifest(
            ["series"], None, config_obj.include_catalogs_series, changed_catalogs=config_obj.changed_catalogs
        )
    except Exception as e:
        logger.error(f"Series manifest request failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid config")


async def _process_catalog_request_internal(
    config: str,
    search: str,
    content_type: ContentType,
    include_adult: bool,
    max_results: int | None = None,
    cache_time_seconds: int | None = None,
    apply_rpdb_posters: bool = True,
):
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

        logger.debug(f"Processing {content_type} catalog request for '{search}' with {max_results} max results")

        key = None
        cache = CACHE_INSTANCE
        if cache_time_seconds is not None:
            try:
                cleaned = slugify(search, separator="")
                if cleaned:
                    key = f"search:{content_type.value}:{cleaned}"
            except Exception:
                key = None

            if key:
                cached_entries = await cache.aget(key)
                if cached_entries is not None and len(cached_entries["metas"]) > 0:
                    logger.debug(f"Cache hit for key={key}")
                    return cached_entries

        llm_service = LLMService(config_obj)
        tmdb_service = TMDBService(config_obj.tmdb_read_access_token, language=config_obj.language)
        rpdb_service = RPDBService(config_obj.posterdb_api_key) if config_obj.use_posterdb else None

        user_intent = detect_user_intent(search)

        if user_intent and user_intent != content_type:
            logger.debug(
                f"User intent '{user_intent}' conflicts with endpoint type '{content_type}', returning empty list"
            )
            result = {"metas": []}
            return result

        if content_type == ContentType.MOVIE:
            movie_suggestions = await llm_service.generate_movie_suggestions(search, max_results)
            logger.debug(
                f"Generated {len(movie_suggestions)} movie suggestions: {[f'{s.title} ({s.year})' for s in movie_suggestions]}"
            )
            movie_metas = await _process_metadata_pipeline(
                tmdb_service,
                rpdb_service,
                movie_suggestions,
                include_adult,
                search_fn=tmdb_service.search_movie,
                details_fn=tmdb_service.get_movie_details,
                meta_builder=movie_to_stremio_meta,
            )
            logger.debug(f"Returning {len(movie_metas)} movie metadata entries")
            result = {"metas": movie_metas}
        else:
            series_suggestions = await llm_service.generate_tv_suggestions(search, max_results)
            logger.debug(
                f"Generated {len(series_suggestions)} TV series suggestions: {[f'{s.title} ({s.year})' for s in series_suggestions]}"
            )
            series_metas = await _process_metadata_pipeline(
                tmdb_service,
                rpdb_service,
                series_suggestions,
                include_adult,
                search_fn=tmdb_service.search_tv,
                details_fn=tmdb_service.get_tv_details,
                meta_builder=tv_to_stremio_meta,
            )
            logger.debug(f"Returning {len(series_metas)} series metadata entries")
            result = {"metas": series_metas}

        # Cache with TMDB posters only
        if cache_time_seconds and key:
            await cache.aset(key, result, ttl=cache_time_seconds)

        # Apply RPDB posters before delivery if user has RPDB enabled and requested
        if apply_rpdb_posters:
            result["metas"] = await _apply_rpdb_posters(result["metas"], rpdb_service)
        return result

    except Exception as e:
        logger.error(f"Catalog request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _process_catalog_request(
    config: str,
    search: str,
    content_type: ContentType,
    include_adult: bool,
    max_results: int | None = None,
    cache_time_seconds: int | None = None,
):
    """
    Public wrapper for catalog processing that always applies RPDB posters.
    """
    return await _process_catalog_request_internal(
        config, search, content_type, include_adult, max_results, cache_time_seconds, apply_rpdb_posters=True
    )


async def _cached_catalog(
    config: str, content_type: ContentType, catalog_id: str | None = None, skip: int = 0, include_adult: bool = False
):
    """
    Cached version of the catalogue view with pagination support (Redis only).
    """
    # Parse config to get RPDB service for poster modification
    config_data = encryption_service.decrypt(config)
    config_obj = Config.model_validate(json.loads(config_data))
    rpdb_service = RPDBService(config_obj.posterdb_api_key) if config_obj.use_posterdb else None

    cache = CACHE_INSTANCE
    catalog_config = CATALOG_PROMPTS.get(catalog_id.rstrip(f"_{content_type.value}"), CATALOG_PROMPTS.get("trending"))
    prompt = catalog_config["prompt"]

    # Get TTL for this specific catalog
    catalog_ttl = catalog_config.get("cache_ttl")
    if callable(catalog_ttl):
        catalog_ttl = catalog_ttl()  # Call function to get dynamic TTL
    elif catalog_ttl is None:
        catalog_ttl = cache.ttl  # Use default cache TTL

    key = f"catalog:{catalog_id}"

    # Pagination only works with Redis cache
    if not cache.is_redis:
        cached_entries = await cache.aget(key)
        if cached_entries is not None and len(cached_entries["metas"]) > 0:
            logger.debug(f"Cache hit for key={key}")
            # Apply RPDB posters before delivery
            cached_entries["metas"] = await _apply_rpdb_posters(cached_entries["metas"], rpdb_service)
            result_names = [meta.get("name", "Unknown") for meta in cached_entries["metas"]]
            logger.debug(
                f"LRU Cache: Returning {len(cached_entries['metas'])} cached_entries items for skip={skip}: {result_names}"
            )
            return cached_entries
        logger.debug(f"Cache miss for key={key}")
        result = await _process_catalog_request_internal(
            config,
            prompt,
            content_type,
            include_adult,
            max_results=settings.MAX_CATALOG_RESULTS,
            cache_time_seconds=None,
            apply_rpdb_posters=False,
        )
        await cache.aset(key, result, catalog_ttl)
        # Apply RPDB posters before delivery
        result["metas"] = await _apply_rpdb_posters(result["metas"], rpdb_service)
        result_names = [meta.get("name", "Unknown") for meta in result["metas"]]
        logger.debug(f"LRU Cache: Returning {len(result['metas'])} items for skip={skip}: {result_names}")
        return result

    # Get existing cached_entries entries
    cached_entries = await cache.aget(key)
    # Check if we have enough entries to satisfy the request
    if cached_entries is not None and len(cached_entries["metas"]) > 0:
        logger.debug(f"Cache hit for key={key}, found {len(cached_entries['metas'])} existing entries")
    else:
        cached_entries = {"metas": []}
        logger.debug(f"Cache miss for key={key}")

    total_entries = len(cached_entries["metas"])
    # Already at max entries, return cached_entries
    if total_entries >= settings.MAX_CATALOG_ENTRIES:
        logger.debug(f"Max catalog entries ({settings.MAX_CATALOG_ENTRIES}) reached for {catalog_id}")
        # Apply RPDB posters before delivery
        cached_entries["metas"] = await _apply_rpdb_posters(cached_entries["metas"], rpdb_service)
        return {"metas": cached_entries["metas"]}

    # Generate new entries, avoiding duplicates
    existing_ids = {meta.get("id") for meta in cached_entries["metas"]}
    existing_titles = {meta.get("name", "").lower() for meta in cached_entries["metas"]}

    # Create prompt that includes existing entries to avoid duplicates
    existing_list = [meta.get("name", "") for meta in cached_entries["metas"]]
    enhanced_prompt = prompt
    if existing_list:
        enhanced_prompt += f"\n\nAvoid recommending these already suggested titles: {', '.join(existing_list)}"

    # Generate more entries - always request more than needed to account for duplicates
    new_result = await _process_catalog_request_internal(
        config,
        enhanced_prompt,
        content_type,
        include_adult,
        max_results=settings.MAX_CATALOG_RESULTS,
        apply_rpdb_posters=False,
    )

    # Filter out duplicates
    new_metas = []
    for meta in new_result["metas"]:
        meta_id = meta.get("id")
        meta_name = meta.get("name", "").lower()
        if meta_id not in existing_ids and meta_name not in existing_titles:
            new_metas.append(meta)
            existing_ids.add(meta_id)
            existing_titles.add(meta_name)

    # Update cache with new entries (only possible with Redis)
    cached_entries["metas"].extend(new_metas)
    await cache.aset(key, cached_entries, catalog_ttl)

    logger.debug(f"Added {len(new_metas)} new entries, total now: {len(cached_entries['metas'])}")

    # Apply RPDB posters before delivery
    cached_entries["metas"] = await _apply_rpdb_posters(cached_entries["metas"], rpdb_service)

    # Return the whole results (cached_entries + new)
    logger.debug(f"Redis Cache: Returning {len(cached_entries['metas'])} total items for skip={skip}")
    return {"metas": cached_entries["metas"]}


@router.get("/config/{config}/adult/{adult}/catalog/{content_type}/{catalog_id}.json")
async def get_catalog(config: str, adult: int, content_type: ContentType, catalog_id: str) -> StremioResponse:
    """
    Path-based catalog endpoint.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """
    content = await _cached_catalog(config, content_type, catalog_id, include_adult=False)
    return StremioResponse(**content)


@router.get("/config/{config}/adult/{adult}/{content_type_extra}/catalog/{content_type}/{catalog_id}.json")
async def get_catalog_split(
    config: str, adult: int, content_type_extra: str | None, content_type: ContentType, catalog_id: str
) -> StremioResponse:
    content = await _cached_catalog(config, content_type, catalog_id, include_adult=False)
    return StremioResponse(**content)


@router.get("/config/{config}/adult/{adult}/catalog/{content_type}/{catalog_id}/skip={skip}.json")
async def get_catalog_with_skip(
    config: str, adult: int, content_type: ContentType, catalog_id: str, skip: int
) -> StremioResponse:
    """
    Path-based catalog endpoint with pagination support.

    This endpoint is called by Stremio when it reaches the end of the catalog list.
    """
    content = await _cached_catalog(config, content_type, catalog_id, skip, include_adult=False)
    return StremioResponse(**content)


@router.get("/config/{config}/adult/{adult}/{content_type_extra}/catalog/{content_type}/{catalog_id}/skip={skip}.json")
async def get_catalog_with_skip_split(
    config: str, adult: int, content_type_extra: str | None, content_type: ContentType, catalog_id: str, skip: int
) -> StremioResponse:
    """
    Path-based catalog endpoint with pagination support.

    This endpoint is called by Stremio when it reaches the end of the catalog list.
    """
    content = await _cached_catalog(config, content_type, catalog_id, skip, include_adult=False)
    return StremioResponse(**content)


@router.get("/config/{config}/adult/{adult}/catalog/{content_type}/{catalog_id}/search={search}.json")
async def get_catalog_search(
    config: str, adult: int, content_type: ContentType, catalog_id: str, search: str
) -> StremioResponse:
    """
    Path-based catalog search endpoint for movies.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """
    # Always use the non-cached version for explicit searches
    content = await _process_catalog_request(
        config, search, content_type, False, cache_time_seconds=settings.CACHE_SEARCH_QUERY_TTL
    )
    return StremioResponse(**content)


@router.get(
    "/config/{config}/adult/{adult}/{content_type_extra}/catalog/{content_type}/{catalog_id}/search={search}.json"
)
async def get_catalog_search_split(
    config: str, adult: int, content_type_extra: str | None, content_type: ContentType, catalog_id: str, search: str
) -> StremioResponse:
    """
    Path-based catalog search endpoint for movies.

    This endpoint is called by Stremio to get movie metadata based on a search query.
    """
    # Always use the non-cached version for explicit searches
    content = await _process_catalog_request(
        config, search, content_type, False, cache_time_seconds=settings.CACHE_SEARCH_QUERY_TTL
    )
    return StremioResponse(**content)


#
