"""
Stremio AI Companion - Your AI-powered movie discovery companion for Stremio

This is the main entry point for the application.
"""

import uvicorn
from app.api import app
from app.core.config import settings
from app.core.logging import logger

if __name__ == "__main__":
    logger.info(f"Starting Stremio AI Companion on {settings.HOST}:{settings.PORT}")
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
