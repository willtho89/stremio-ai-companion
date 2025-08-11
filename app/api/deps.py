from functools import wraps
from typing import Callable, Awaitable, Any

from fastapi import Path, HTTPException

from app.core.logging import logger
from app.models.config import Config
from app.models.movie import StremioResponse
from app.services.encryption import encryption_service
from app.services.rpdb import RPDBService


def get_config(config: str = Path(...)) -> Config:
    try:
        raw = encryption_service.decrypt(config)
        # decrypt() may already return JSON string
        return Config.model_validate_json(raw)
    except HTTPException:
        # Bubble up the HTTPException raised by encryption_service for invalid data
        raise
    except Exception:
        # If decrypt didn't raise HTTPException (e.g., mock returns JSON string), try direct parse of the path segment
        try:
            return Config.model_validate_json(config)
        except Exception as e2:
            logger.error(f"Config decrypt/parse failed: {e2}")
            raise HTTPException(status_code=400, detail="Invalid config data")


def rpdb_response(func: Callable[..., Awaitable[dict]]):
    """Apply RPDB posters to response metas if enabled in cfg.
    The wrapped function must accept a keyword argument 'cfg: Config'.
    """

    async def _apply(result: StremioResponse, cfg: Config) -> StremioResponse:
        if cfg and getattr(cfg, "use_posterdb", False):
            svc = RPDBService(cfg.posterdb_api_key)
            # mutate a copy to avoid altering cached payloads
            for meta in result.metas:
                if meta.imdb_id:
                    poster = svc.get_poster(meta.imdb_id)
                    if poster:
                        meta.poster = poster
        return result

    @wraps(func)
    async def wrapper(*args, **kwargs):
        cfg: Config = kwargs.get("cfg")
        result: Any = await func(*args, **kwargs)
        if isinstance(result, StremioResponse) and cfg is not None:
            result = await _apply(result, cfg)
        return result

    return wrapper
