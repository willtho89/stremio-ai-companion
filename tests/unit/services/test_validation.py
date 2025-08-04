"""
Tests for the configuration validation service.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx
import openai

from app.models.config import Config
from app.services.validation import ConfigValidationService, ValidationError


@pytest.fixture
def validation_service():
    """Create a validation service instance."""
    return ConfigValidationService()


@pytest.fixture
def valid_config():
    """Create a valid configuration for testing."""
    return Config(
        openai_api_key="test-api-key",
        openai_base_url="https://api.openai.com/v1",
        model_name="gpt-3.5-turbo",
        tmdb_read_access_token="test-tmdb-token",
        max_results=20,
        use_posterdb=True,
        posterdb_api_key="test-rpdb-key",
    )


class TestLLMValidation:
    """Test LLM connection validation."""

    @patch("openai.AsyncOpenAI")
    async def test_validate_llm_connection_success(self, mock_openai, validation_service, valid_config):
        """Test successful LLM connection validation."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "OK"

        mock_client = AsyncMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        # Should not raise any exception
        await validation_service.validate_llm_connection(valid_config)

        # Verify the client was created with correct parameters
        mock_openai.assert_called_once_with(
            api_key=valid_config.openai_api_key,
            base_url=valid_config.openai_base_url,
            timeout=validation_service._timeout,
        )

    @patch("openai.AsyncOpenAI")
    async def test_validate_llm_connection_auth_error(self, mock_openai, validation_service, valid_config):
        """Test LLM validation with authentication error."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_client.chat.completions.create.side_effect = openai.AuthenticationError(
            "Invalid API key", response=mock_response, body={}
        )
        mock_openai.return_value = mock_client

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_llm_connection(valid_config)

        assert exc_info.value.service == "LLM"
        assert "Invalid API key" in exc_info.value.message

    @patch("openai.AsyncOpenAI")
    async def test_validate_llm_connection_model_not_found(self, mock_openai, validation_service, valid_config):
        """Test LLM validation with model not found error."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.chat.completions.create.side_effect = openai.NotFoundError(
            "Model not found", response=mock_response, body={}
        )
        mock_openai.return_value = mock_client

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_llm_connection(valid_config)

        assert exc_info.value.service == "LLM"
        assert "not found" in exc_info.value.message


class TestTMDBValidation:
    """Test TMDB connection validation."""

    @patch("httpx.AsyncClient")
    async def test_validate_tmdb_connection_success(self, mock_client_class, validation_service, valid_config):
        """Test successful TMDB connection validation."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"images": {"base_url": "https://image.tmdb.org/"}}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Should not raise any exception
        await validation_service.validate_tmdb_connection(valid_config)

    @patch("httpx.AsyncClient")
    async def test_validate_tmdb_connection_auth_error(self, mock_client_class, validation_service, valid_config):
        """Test TMDB validation with authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_tmdb_connection(valid_config)

        assert exc_info.value.service == "TMDB"
        assert "Invalid access token" in exc_info.value.message

    @patch("httpx.AsyncClient")
    async def test_validate_tmdb_connection_timeout(self, mock_client_class, validation_service, valid_config):
        """Test TMDB validation with timeout error."""
        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timeout")
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_tmdb_connection(valid_config)

        assert exc_info.value.service == "TMDB"
        assert "timed out" in exc_info.value.message


class TestRPDBValidation:
    """Test RPDB connection validation."""

    @patch("httpx.AsyncClient")
    async def test_validate_rpdb_connection_success(self, mock_client_class, validation_service, valid_config):
        """Test successful RPDB connection validation."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Should not raise any exception
        await validation_service.validate_rpdb_connection(valid_config)

    @patch("httpx.AsyncClient")
    async def test_validate_rpdb_connection_404_acceptable(self, mock_client_class, validation_service, valid_config):
        """Test RPDB validation where 404 is acceptable (API key works but image doesn't exist)."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        # Should not raise any exception (404 is acceptable for test image)
        await validation_service.validate_rpdb_connection(valid_config)

    async def test_validate_rpdb_connection_disabled(self, validation_service):
        """Test RPDB validation when RPDB is disabled."""
        config = Config(
            openai_api_key="test-api-key-long-enough",
            model_name="test-model",
            tmdb_read_access_token="test-token-long-enough",
            use_posterdb=False,
        )

        # Should not raise any exception when RPDB is disabled
        await validation_service.validate_rpdb_connection(config)

    @patch("httpx.AsyncClient")
    async def test_validate_rpdb_connection_auth_error(self, mock_client_class, validation_service, valid_config):
        """Test RPDB validation with authentication error."""
        mock_response = MagicMock()
        mock_response.status_code = 401

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response
        mock_client_class.return_value.__aenter__.return_value = mock_client

        with pytest.raises(ValidationError) as exc_info:
            await validation_service.validate_rpdb_connection(valid_config)

        assert exc_info.value.service == "RPDB"
        assert "Invalid API key" in exc_info.value.message


class TestFullValidation:
    """Test full configuration validation."""

    @patch("app.services.validation.ConfigValidationService.validate_rpdb_connection")
    @patch("app.services.validation.ConfigValidationService.validate_tmdb_connection")
    @patch("app.services.validation.ConfigValidationService.validate_llm_connection")
    async def test_validate_config_all_success(self, mock_llm, mock_tmdb, mock_rpdb, validation_service, valid_config):
        """Test full validation when all services are working."""
        # All validations succeed
        mock_llm.return_value = None
        mock_tmdb.return_value = None
        mock_rpdb.return_value = None

        errors = await validation_service.validate_config(valid_config)

        assert errors == {}

    @patch("app.services.validation.ConfigValidationService.validate_rpdb_connection")
    @patch("app.services.validation.ConfigValidationService.validate_tmdb_connection")
    @patch("app.services.validation.ConfigValidationService.validate_llm_connection")
    async def test_validate_config_with_errors(self, mock_llm, mock_tmdb, mock_rpdb, validation_service, valid_config):
        """Test full validation when some services fail."""
        # LLM fails, others succeed
        mock_llm.side_effect = ValidationError("LLM", "Invalid API key")
        mock_tmdb.return_value = None
        mock_rpdb.return_value = None

        errors = await validation_service.validate_config(valid_config)

        assert "LLM" in errors
        assert errors["LLM"] == "Invalid API key"
        assert len(errors) == 1

    def test_format_validation_errors(self, validation_service):
        """Test error message formatting."""
        errors = {"LLM": "Invalid API key", "TMDB": "Connection timeout", "RPDB": "Service unavailable"}

        formatted = validation_service.format_validation_errors(errors)

        assert "Configuration validation failed:" in formatted
        assert "• LLM: Invalid API key" in formatted
        assert "• TMDB: Connection timeout" in formatted
        assert "• RPDB: Service unavailable" in formatted

    def test_format_validation_errors_empty(self, validation_service):
        """Test error message formatting with no errors."""
        errors = {}
        formatted = validation_service.format_validation_errors(errors)
        assert formatted == ""
