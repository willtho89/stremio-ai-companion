"""
API routes for the Stremio AI Companion application.
"""

from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

from app.api.stremio import router as stremio_router
from app.api.web import router as web_router
from app.core.logging import logger
from app import __version__

# Create FastAPI app
app = FastAPI(
    title="Stremio AI Companion",
    description="Your AI-powered movie discovery companion for Stremio",
    version=__version__,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their responses."""
    start_time = datetime.now()
    logger.info(f"{request.method} {request.url} - Headers: {dict(request.headers)}")
    response = await call_next(request)
    duration = datetime.now() - start_time
    logger.info(f"Response: {response.status_code} - Duration: {duration.total_seconds()}s")
    return response


# Include routers
app.include_router(web_router)
app.include_router(stremio_router)
