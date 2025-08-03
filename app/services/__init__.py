"""
Service classes for the Stremio AI Companion application.
"""

from .llm import LLMService
from .tmdb import TMDBService
from .rpdb import RPDBService
from .encryption import encryption_service

CATALOG_PROMPTS = {
    "trending": {
        "title": "Trending this week",
        "prompt": "Show me what's trending this week on streaming services (priority), but include notable on-demand rentals or Blu-ray releases if relevant",
    },
    "new_releases": {
        "title": "New releases",
        "prompt": "Show me the latest new releases available to stream right now; also include notable on-demand rentals or Blu-ray releases when applicable",
    },
    "critics_picks": {
        "title": "Critics' picks",
        "prompt": "Show me highly-rated titles from critics and award winners that are available on streaming services; optionally include notable on-demand or Blu-ray if streaming is unavailable",
    },
    "hidden_gems": {
        "title": "Hidden gems",
        "prompt": "Show me underrated or lesser-known titles worth watching on streaming services; if not streaming, include notable on-demand or Blu-ray",
    },
}
