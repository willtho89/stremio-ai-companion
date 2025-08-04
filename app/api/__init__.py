"""
API routes for the Stremio AI Companion application.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.staticfiles import StaticFiles

from app import __version__
from app.api.stremio import router as stremio_router
from app.api.web import router as web_router
from app.core.logging import logger
from app.services.cache import CACHE_INSTANCE


@asynccontextmanager
async def lifespan(app: FastAPI):
    cache = CACHE_INSTANCE
    if cache.is_redis:
        try:
            await cache._redis.ping()  # type: ignore
            logger.info("Cache backend: Redis connected on startup")
        except Exception:
            logger.warning("Redis configured but unreachable on startup; falling back to LRU")
    else:
        logger.info("Cache backend: in-memory LRU")
    yield


# Create FastAPI app
app = FastAPI(
    title="Stremio AI Companion",
    description="Your AI-powered movie discovery companion for Stremio",
    version=__version__,
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.mount("/static", StaticFiles(directory="./.assets"), name="static")

app.add_middleware(GZipMiddleware, compresslevel=9)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their responses."""
    start_time = datetime.now()
    url_str = str(request.url)
    if "/config/" in url_str:
        base, rest = url_str.split("/config/", 1)
        # mask up to the next '/'
        masked = rest
        if "/" in rest:
            token, tail = rest.split("/", 1)
            # also handle base64 padding marker '==' cases inside token
            token = token.split("==", 1)[0]
            masked = f"****/{tail}"
        safe_url = f"{base}/config/{masked}"
    else:
        safe_url = url_str
    logger.info(f"{request.method} {safe_url}")
    response = await call_next(request)
    duration = datetime.now() - start_time
    logger.info(f"Response: {response.status_code} - Duration: {duration.total_seconds()}s")
    return response


# Include routers
app.include_router(web_router)
app.include_router(stremio_router)
