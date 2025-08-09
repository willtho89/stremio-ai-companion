"""
Tests for the Config model.
"""

import pytest
from pydantic import ValidationError

from app.models.config import Config


class TestConfig:
    """Tests for the Config model."""

    def test_valid_config(self):
        """Test creating a valid Config object."""
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            openai_base_url="https://openrouter.ai/api/v1",
            model_name="openai/gpt-5-mini:online",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
            max_results=20,
            use_posterdb=False,
            posterdb_api_key=None,
        )

        assert config.openai_api_key == "sk-test123456789012345678901234567890"
        assert config.openai_base_url == "https://openrouter.ai/api/v1"
        assert config.model_name == "openai/gpt-5-mini:online"
        assert config.tmdb_read_access_token == "eyJhbGciOiJIUzI1NiJ9.test1234567890"
        assert config.max_results == 20
        assert config.use_posterdb is False
        assert config.posterdb_api_key is None

    def test_default_values(self):
        """Test default values for optional fields."""
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
        )

        assert config.openai_base_url == "https://openrouter.ai/api/v1"
        assert config.model_name == "openai/gpt-5-mini:online"
        assert config.max_results == 20
        assert config.use_posterdb is False
        # posterdb_api_key may be set from environment, so we don't assert it's None

    def test_invalid_openai_api_key(self):
        """Test validation for invalid OpenAI API key."""
        with pytest.raises(ValidationError) as exc_info:
            Config(openai_api_key="", tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890")

        assert "OpenAI API key must be provided and valid" in str(exc_info.value)

    def test_invalid_tmdb_token(self):
        """Test validation for invalid TMDB token."""
        with pytest.raises(ValidationError) as exc_info:
            Config(openai_api_key="sk-test123456789012345678901234567890", tmdb_read_access_token="")

        assert "TMDB read access token must be provided and valid" in str(exc_info.value)

    def test_invalid_max_results_low(self):
        """Test validation for max_results below minimum."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                openai_api_key="sk-test123456789012345678901234567890",
                tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
                max_results=0,
            )

        assert "Max results must be at least 1" in str(exc_info.value)

    def test_invalid_openai_url(self):
        """Test validation for invalid OpenAI base URL."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                openai_api_key="sk-test123456789012345678901234567890",
                tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
                openai_base_url="invalid-url",
            )

        assert "OpenAI base URL must be a valid HTTP/HTTPS URL" in str(exc_info.value)

    def test_missing_posterdb_key(self):
        """Test validation for missing RPDB API key when RPDB is enabled."""
        with pytest.raises(ValidationError) as exc_info:
            Config(
                openai_api_key="sk-test123456789012345678901234567890",
                tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
                use_posterdb=True,
                posterdb_api_key=None,
            )

        assert "RPDB API key is required when RPDB is enabled" in str(exc_info.value)

    def test_posterdb_key_not_required_when_disabled(self):
        """Test that RPDB API key is not required when RPDB is disabled."""
        config = Config(
            openai_api_key="sk-test123456789012345678901234567890",
            tmdb_read_access_token="eyJhbGciOiJIUzI1NiJ9.test1234567890",
            use_posterdb=False,
            posterdb_api_key=None,
        )

        assert config.use_posterdb is False
        assert config.posterdb_api_key is None
