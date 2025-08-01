"""
Application configuration settings for the Stremio AI Companion.
"""

from functools import lru_cache

from pydantic import BaseModel


class Settings(BaseModel):
    """
    Application settings loaded from environment variables.
    """

    # Application settings
    APP_NAME: str = "Stremio AI Companion"
    APP_VERSION: str = "0.0.1"
    APP_DESCRIPTION: str = "Your AI-powered movie discovery companion for Stremio"

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Logging
    LOG_LEVEL: str = "INFO"

    # Security
    ENCRYPTION_KEY: str = "stremio-ai-companion-default-key"

    # API settings
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    DEFAULT_MODEL: str = "gpt-4.1-mini"

    # TMDB settings
    TMDB_READ_ACCESS_TOKEN: str = ""

    # RPDB settings
    RPDB_API_KEY: str = ""

    model_config = {"extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings, cached for performance.

    Returns:
        Settings object with application configuration
    """
    return Settings()


# Export settings instance for easy access
settings = get_settings()
