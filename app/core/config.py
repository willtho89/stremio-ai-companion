"""
Application configuration settings for the Stremio AI Companion.
"""

import os
from functools import lru_cache
from app import __version__
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="")

    # Application settings
    APP_NAME: str = Field(default="Stremio AI Companion")
    APP_VERSION: str = Field(default=__version__)
    APP_DESCRIPTION: str = Field(default="Your AI-powered movie discovery companion for Stremio")
    STREMIO_ADDON_ID: str = Field(default="ai.companion.stremio", description="Stremio addon ID")

    # Server settings
    HOST: str = Field(default="0.0.0.0")
    PORT: int = Field(default=8000)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")

    # Security
    ENCRYPTION_KEY: str = Field(description="Required encryption key for securing configuration data", min_length=4)

    # API settings
    OPENAI_API_KEY: str | None = Field(default=None)
    OPENAI_BASE_URL: str = Field(default="https://openrouter.ai/api/v1")
    DEFAULT_MODEL: str = Field(default="openrouter/horizon-beta:online")

    # TMDB settings
    TMDB_READ_ACCESS_TOKEN: str | None = Field(default=None, alias="TMDB_API_KEY")

    # RPDB settings
    RPDB_API_KEY: str | None = Field(default=None)

    # Catalog settings
    MAX_CATALOG_RESULTS: int = Field(default=10, description="Maximum number of results to return in cached catalog")
    MAX_CATALOG_ENTRIES: int = Field(default=100, description="Maximum total entries to store per catalog")

    # Manifest settings
    SPLIT_MANIFESTS: bool = Field(default=False, description="Enable split manifests for movie/series types")
    ENABLE_FEED_CATALOGS: bool = Field(default=True, description="Expose predefined feed catalogs in manifest")
    REDIS_HOST: str | None = Field(default=None, description="Redis host if URL not provided")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    REDIS_DB: int = Field(default=0, description="Redis DB index")
    CACHE_SEARCH_QUERY_TTL: int = Field(default=14400, description="TTL for cached search queries")  # default 4h

    # Customizing
    FOOTER_ENABLED: bool = Field(default=True, description="Show footer on pages")


class TestSettings(Settings):
    """
    Test-specific settings that don't load from .env file.
    """

    FOOTER_ENABLED: bool = Field(default=True)

    model_config = SettingsConfigDict(extra="ignore", env_file=None)

    # Override required field with test default
    ENCRYPTION_KEY: str = Field(default="test-encryption-key-for-testing")


@lru_cache()
def get_settings() -> Settings:
    """
    Get application settings, cached for performance.

    Returns:
        Settings object with application configuration
    """
    # Use test settings if we're in a test environment
    if os.getenv("PYTEST_VERSION"):
        return TestSettings()
    return Settings()


# Export settings instance for easy access
settings = get_settings()
