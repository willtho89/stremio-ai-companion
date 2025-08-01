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

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Application settings
    APP_NAME: str = Field(default="Stremio AI Companion")
    APP_VERSION: str = Field(default=__version__)
    APP_DESCRIPTION: str = Field(default="Your AI-powered movie discovery companion for Stremio")

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
    DEFAULT_MODEL: str = Field(default="openrouter/horizon-alpha:online")

    # TMDB settings
    TMDB_READ_ACCESS_TOKEN: str | None = Field(default=None, alias="TMDB_API_KEY")

    # RPDB settings
    RPDB_API_KEY: str | None = Field(default=None)


class TestSettings(Settings):
    """
    Test-specific settings that don't load from .env file.
    """

    model_config = SettingsConfigDict(extra="ignore")

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
