"""
Service classes for the Stremio AI Companion application.
"""

from .llm import LLMService
from .tmdb import TMDBService
from .rpdb import RPDBService
from .encryption import encryption_service

import datetime


def get_next_tuesday():
    """Get the next Tuesday at midnight UTC."""
    today = datetime.datetime.now(datetime.timezone.utc)
    days_ahead = 1 - today.weekday()  # Tuesday is 1 (Monday is 0)
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7
    next_tuesday = today + datetime.timedelta(days=days_ahead)
    return next_tuesday.replace(hour=0, minute=0, second=0, microsecond=0)


def get_tuesday_to_tuesday_ttl():
    """Get TTL in seconds from now until next Tuesday."""
    next_tuesday = get_next_tuesday()
    now = datetime.datetime.now(datetime.timezone.utc)
    return int((next_tuesday - now).total_seconds())


CATALOG_PROMPTS = {
    "trending": {
        "title": "Trending this week",
        "prompt": "Show me what's trending this week on streaming services (priority), but include notable on-demand rentals or Blu-ray releases if relevant",
        "cache_ttl": get_tuesday_to_tuesday_ttl,  # Dynamic TTL until next Tuesday
    },
    "new_releases": {
        "title": "New releases",
        "prompt": "Show me the latest new releases available to stream right now; also include notable on-demand rentals or Blu-ray releases when applicable",
        "cache_ttl": 172800,  # 48 hours
    },
    "critics_picks": {
        "title": "Critics' picks",
        "prompt": "Show me highly-rated titles from critics and award winners that are available on streaming services; optionally include notable on-demand or Blu-ray if streaming is unavailable",
        "cache_ttl": 604.800,  # 7 days
    },
    "hidden_gems": {
        "title": "Hidden gems",
        "prompt": "Show me underrated or lesser-known titles worth watching on streaming services; if not streaming, include notable on-demand or Blu-ray",
        "cache_ttl": 1209600,  # 14 days
    },
}
