"""
Configuration validation service for the Stremio AI Companion application.
"""

import logging
from typing import Dict

import httpx
import openai
from openai.types.chat import ChatCompletionUserMessageParam

from app.models.config import Config
from app.services.tmdb import TMDBService


class ValidationError(Exception):
    """Custom exception for validation errors."""

    def __init__(self, service: str, message: str):
        self.service = service
        self.message = message
        super().__init__(f"{service}: {message}")


class ConfigValidationService:
    """
    Service for validating configuration settings by testing connections
    to external services.
    """

    def __init__(self):
        self.logger = logging.getLogger("stremio_ai_companion.ConfigValidationService")
        self._timeout = 10.0

    async def validate_llm_connection(self, config: Config) -> None:
        """
        Test LLM connection by sending a minimal request.

        Args:
            config: Configuration object with LLM settings

        Raises:
            ValidationError: If LLM connection fails
        """
        try:
            client = openai.AsyncOpenAI(
                api_key=config.openai_api_key, base_url=config.openai_base_url, timeout=self._timeout
            )

            # Send a minimal test request
            messages = [
                ChatCompletionUserMessageParam(role="user", content="Test"),
            ]

            response = await client.chat.completions.create(
                model=config.model_name,
                messages=messages,
                max_tokens=30,
                temperature=0,
                reasoning_effort="low",
            )

            if not response.choices:
                raise ValidationError("LLM", "No response received from the model")

            if response.choices[0].message.content is None:
                raise ValidationError("LLM", "Response content is None")

            self.logger.debug("LLM connection test successful")

        except openai.AuthenticationError:
            raise ValidationError("LLM", "Invalid API key - please check your OpenAI API key")
        except openai.NotFoundError:
            raise ValidationError("LLM", f"Model '{config.model_name}' not found - please check the model name")
        except openai.PermissionDeniedError:
            raise ValidationError("LLM", "Permission denied - your API key may not have access to this model")
        except openai.RateLimitError:
            raise ValidationError("LLM", "Rate limit exceeded - please try again later")
        except openai.APIConnectionError:
            raise ValidationError(
                "LLM", f"Cannot connect to API at {config.openai_base_url} - please check the base URL"
            )
        except openai.APITimeoutError:
            raise ValidationError("LLM", "Request timed out - the API may be experiencing issues")
        except Exception as e:
            raise ValidationError("LLM", f"Connection failed: {str(e)}")

    async def validate_tmdb_connection(self, config: Config) -> None:
        """
        Test TMDB connection by making a simple API request.

        Args:
            config: Configuration object with TMDB settings

        Raises:
            ValidationError: If TMDB connection fails
        """
        try:
            tmdb_service = TMDBService(config.tmdb_read_access_token, language=config.language, timeout=self._timeout)

            # Test with a simple configuration endpoint
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{tmdb_service.base_url}/configuration", headers=tmdb_service._headers)

                if response.status_code == 401:
                    raise ValidationError("TMDB", "Invalid access token - please check your TMDB read access token")
                elif response.status_code == 403:
                    raise ValidationError("TMDB", "Access forbidden - your token may not have the required permissions")
                elif response.status_code == 404:
                    raise ValidationError("TMDB", "TMDB API endpoint not found - service may be unavailable")

                response.raise_for_status()
                data = response.json()

                if not data or "images" not in data:
                    raise ValidationError("TMDB", "Invalid response from TMDB API")

            self.logger.debug("TMDB connection test successful")

        except httpx.TimeoutException:
            raise ValidationError("TMDB", "Connection timed out - TMDB API may be experiencing issues")
        except httpx.ConnectError:
            raise ValidationError("TMDB", "Cannot connect to TMDB API - please check your internet connection")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise ValidationError("TMDB", "Invalid access token - please check your TMDB read access token")
            else:
                raise ValidationError("TMDB", f"HTTP error {e.response.status_code}: {e.response.text}")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError("TMDB", f"Connection failed: {str(e)}")

    async def validate_rpdb_connection(self, config: Config) -> None:
        """
        Test RPDB connection if configured.

        Args:
            config: Configuration object with RPDB settings

        Raises:
            ValidationError: If RPDB connection fails when enabled
        """
        if not config.use_posterdb or not config.posterdb_api_key:
            self.logger.debug("RPDB not configured, skipping validation")
            return

        try:
            # Test RPDB by checking if we can access the API with a known IMDB ID
            test_imdb_id = "tt0111161"  # The Shawshank Redemption
            test_url = (
                f"https://api.ratingposterdb.com/{config.posterdb_api_key}/imdb/poster-default/{test_imdb_id}.jpg"
            )

            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.head(test_url)

                if response.status_code == 401:
                    raise ValidationError("RPDB", "Invalid API key - please check your RPDB API key")
                elif response.status_code == 403:
                    raise ValidationError(
                        "RPDB", "Access forbidden - your API key may not have the required permissions"
                    )
                elif response.status_code == 404:
                    # 404 is acceptable for the test image, it means the API key works
                    pass
                elif response.status_code >= 400:
                    raise ValidationError("RPDB", f"API error {response.status_code} - please check your RPDB API key")

            self.logger.debug("RPDB connection test successful")

        except httpx.TimeoutException:
            raise ValidationError("RPDB", "Connection timed out - RPDB API may be experiencing issues")
        except httpx.ConnectError:
            raise ValidationError("RPDB", "Cannot connect to RPDB API - please check your internet connection")
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError("RPDB", f"Connection failed: {str(e)}")

    async def validate_config(self, config: Config) -> Dict[str, str]:
        """
        Validate all configured services and return any errors.

        Args:
            config: Configuration object to validate

        Returns:
            Dictionary mapping service names to error messages (empty if all valid)
        """
        errors = {}

        # Test LLM connection
        try:
            await self.validate_llm_connection(config)
        except ValidationError as e:
            errors[e.service] = e.message
        except Exception as e:
            errors["LLM"] = f"Unexpected error: {str(e)}"

        # Test TMDB connection
        try:
            await self.validate_tmdb_connection(config)
        except ValidationError as e:
            errors[e.service] = e.message
        except Exception as e:
            errors["TMDB"] = f"Unexpected error: {str(e)}"

        # Test RPDB connection if configured
        try:
            await self.validate_rpdb_connection(config)
        except ValidationError as e:
            errors[e.service] = e.message
        except Exception as e:
            errors["RPDB"] = f"Unexpected error: {str(e)}"

        return errors

    def format_validation_errors(self, errors: Dict[str, str]) -> str:
        """
        Format validation errors into a user-friendly message.

        Args:
            errors: Dictionary of service names to error messages

        Returns:
            Formatted error message string
        """
        if not errors:
            return ""

        error_lines = []
        for service, message in errors.items():
            error_lines.append(f"• {service}: {message}")

        return "Configuration validation failed:\n" + "\n".join(error_lines)
