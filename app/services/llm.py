"""
LLM service for the Stremio AI Companion application.
"""

import json
import logging
from datetime import datetime
from typing import List, Type, Tuple, Iterable

import openai
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from pydantic import BaseModel

from app.models.config import Config
from app.models.enums import ContentType
from app.models.movie import MovieSuggestions, TVSeriesSuggestions

MESSAGE_TYPE = Iterable[ChatCompletionSystemMessageParam | ChatCompletionUserMessageParam,]


class LLMService:
    """
    Service for generating movie suggestions using OpenAI's LLM.
    """

    def __init__(self, config: Config):
        self.client = openai.AsyncOpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
        self.model = config.model_name
        self.logger = logging.getLogger("stremio_ai_companion.LLMService")
        self._default_timeout = 30
        self._default_temperature = 0.7
        self._default_max_tokens = 5000

    @property
    def _current_date(self) -> str:
        return datetime.now().strftime("%B %Y")

    def _build_messages(self, query: str, max_results: int, content_type: ContentType) -> MESSAGE_TYPE:
        """
        Build the messages for the API call.

        Args:
            query: User search query
            max_results: Maximum number of results to return
            content_type: Type of content (movie or series)

        Returns:
            A list of messages for the OpenAI API.
        """
        base_instructions = {
            ContentType.MOVIE: {
                "companion_type": "movie discovery AI companion",
                "content_name": "movie",
                "content_plural": "movies",
                "date_description": "release year",
                "example_format": "Movie Title (YYYY)",
            },
            ContentType.SERIES: {
                "companion_type": "TV series discovery AI companion",
                "content_name": "TV series",
                "content_plural": "TV series",
                "date_description": "first air year",
                "example_format": "Series Title (YYYY)",
            },
        }
        instructions = base_instructions[content_type]

        # This prompt is now simplified. It focuses on the *task* because
        # the Structured Output feature handles the schema formatting.
        system_prompt = f"""You are a {instructions['companion_type']}. Today is {self._current_date}.
Your task is to generate {instructions['content_name']} titles that perfectly match the user's search query.

Focus on understanding the user's mood, preferences, and context. If they mention themes, genres, time periods, or specific feelings, find {instructions['content_plural']} that truly capture those elements.
If you can use web search, rely on classical media, letterboxd, TMDB, Trakt for recommendations.

IMPORTANT: Each suggested title string MUST include its {instructions['date_description']} in parentheses, like "{instructions['example_format']}". This is critical for accurate identification."""

        user_prompt = f"""Generate {max_results} {instructions['content_plural']} for the query: "{query}"."""

        return [
            ChatCompletionSystemMessageParam(role="system", content=system_prompt),
            ChatCompletionUserMessageParam(role="user", content=user_prompt),
        ]

    def _get_response_config(self, content_type: ContentType) -> Tuple[Type[BaseModel], str]:
        config_map = {
            ContentType.MOVIE: (MovieSuggestions, "movies"),
            ContentType.SERIES: (TVSeriesSuggestions, "series"),
        }
        return config_map[content_type]

    async def _try_structured_completion(
        self, messages: MESSAGE_TYPE, response_model: Type[BaseModel], field_name: str, max_results: int
    ) -> List[str]:
        """
        Attempt to get structured completion from OpenAI using .parse().
        This is OpenAI's recommended approach for reliable, schema-enforced output.
        """
        self.logger.debug(f"Attempting Structured Output with model '{self.model}'")
        # The .parse() method directly uses the pydantic model to enforce the output structure.
        # This is more reliable than JSON mode.
        response = await self.client.chat.completions.parse(
            model=self.model,
            messages=messages,
            response_format=response_model,
            temperature=self._default_temperature,
            max_tokens=self._default_max_tokens,
            timeout=self._default_timeout,
        )

        parsed_object = response.choices[0].message.parsed
        if not parsed_object:
            raise ValueError("Structured output parsing returned a null object.")

        items = getattr(parsed_object, field_name)
        self.logger.debug(f"Successfully parsed {len(items)} items using Structured Output.")
        return items[:max_results]

    async def _try_fallback_completion(
        self, messages: MESSAGE_TYPE, response_model: Type[BaseModel], field_name: str, max_results: int
    ) -> List[str]:
        """
        Attempt fallback using JSON Mode. This is for models that may not
        support the more advanced Structured Outputs feature.
        """
        self.logger.warning("Falling back to JSON Mode.")

        # Add a final instruction to the messages to strongly request JSON.
        messages_with_fallback = messages + [
            {
                "role": "system",
                "content": f"You must respond with a valid JSON object that conforms to this schema: {json.dumps(response_model.model_json_schema())}",
            }
        ]

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages_with_fallback,
            response_format={"type": "json_object"},
            temperature=self._default_temperature,
            max_tokens=self._default_max_tokens,
            timeout=self._default_timeout,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("Fallback completion returned empty content.")

        # Manually parse and validate the JSON with Pydantic
        parsed_data = response_model.model_validate_json(content)
        items = getattr(parsed_data, field_name)

        self.logger.debug(f"Successfully parsed {len(items)} items from fallback completion.")
        return items[:max_results]

    async def _generate_suggestions(self, query: str, max_results: int, *, content_type: ContentType) -> List[str]:
        """
        Generate content suggestions, prioritizing Structured Outputs and then
        falling back to JSON mode if necessary.
        """
        self.logger.debug(f"Generating {max_results} {content_type.value} suggestions for query: '{query}'")

        messages = self._build_messages(query, max_results, content_type)
        response_model, field_name = self._get_response_config(content_type)

        try:
            # First, try the best-practice method. Your original instinct was correct.
            return await self._try_structured_completion(messages, response_model, field_name, max_results)
        except (openai.BadRequestError, AttributeError) as e:
            # This block gracefully handles cases where the model/endpoint does not support
            # the .parse() method or structured outputs. For example, some older models
            # or proxy servers might not support it. It's often indicated by a BadRequestError.
            self.logger.warning(f"Structured Output (.parse) failed: {e}. Attempting fallback.")
            try:
                return await self._try_fallback_completion(messages, response_model, field_name, max_results)
            except Exception as fallback_e:
                self.logger.error(f"Fallback completion also failed: {fallback_e}")
                return [query]  # Final fallback
        except Exception as e:
            self.logger.error(f"An unexpected LLM service error occurred: {e}")
            return [query]

    # ... The rest of your class is perfect and does not need changes.
    async def generate_movie_suggestions(self, query: str, max_results: int) -> List[str]:
        return await self._generate_suggestions(query, max_results, content_type=ContentType.MOVIE)

    async def generate_tv_suggestions(self, query: str, max_results: int) -> List[str]:
        return await self._generate_suggestions(query, max_results, content_type=ContentType.SERIES)
