"""
Configuration models for the Stremio AI Companion application.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.config import settings


class Config(BaseModel):
    """
    Configuration model for the Stremio AI Companion.

    This model stores user-specific configuration settings that are
    encrypted and stored in URL parameters.
    """

    model_config = ConfigDict(protected_namespaces=())

    openai_api_key: str = ""
    openai_base_url: Optional[str] = None
    model_name: str = ""
    tmdb_read_access_token: str = ""
    max_results: int = 20
    use_posterdb: bool = False
    posterdb_api_key: Optional[str] = None
    include_catalogs_movies: Optional[list[str]] = None
    include_catalogs_series: Optional[list[str]] = None
    changed_catalogs: bool = False

    def __init__(self, **data):
        # Use .env values as defaults if not provided (but not if explicitly set to empty)
        if "openai_api_key" not in data and settings.OPENAI_API_KEY:
            data["openai_api_key"] = settings.OPENAI_API_KEY
        if "openai_base_url" not in data and settings.OPENAI_BASE_URL:
            data["openai_base_url"] = settings.OPENAI_BASE_URL
        if "model_name" not in data and settings.DEFAULT_MODEL:
            data["model_name"] = settings.DEFAULT_MODEL
        if "tmdb_read_access_token" not in data and settings.TMDB_READ_ACCESS_TOKEN:
            data["tmdb_read_access_token"] = settings.TMDB_READ_ACCESS_TOKEN
        if "posterdb_api_key" not in data and settings.RPDB_API_KEY:
            data["posterdb_api_key"] = settings.RPDB_API_KEY

        super().__init__(**data)

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_key(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("OpenAI API key must be provided and valid")
        return v.strip()

    @field_validator("tmdb_read_access_token")
    @classmethod
    def validate_tmdb_token(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError("TMDB read access token must be provided and valid")
        return v.strip()

    @field_validator("max_results")
    @classmethod
    def validate_max_results(cls, v):
        if v < 1 or v > 50:
            raise ValueError("Max results must be between 1 and 50")
        return v

    @field_validator("openai_base_url")
    @classmethod
    def validate_openai_url(cls, v):
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("OpenAI base URL must be a valid HTTP/HTTPS URL")
        return v

    @field_validator("posterdb_api_key")
    @classmethod
    def validate_posterdb_key(cls, v, info):
        if info.data.get("use_posterdb") and (not v or len(v.strip()) < 5):
            raise ValueError("RPDB API key is required when RPDB is enabled")
        return v.strip() if v else None
