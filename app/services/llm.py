"""
LLM service for the Stremio AI Companion application.
"""

import json
import logging
from datetime import datetime
from typing import List, Type, Tuple, Iterable, Union, cast

import openai
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
from pydantic import BaseModel

from app.models.config import Config
from app.models.enums import ContentType
from app.models.movie import MovieSuggestions, TVSeriesSuggestions, MovieSuggestion, TVSeriesSuggestion

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

    @property
    def _current_year(self) -> int:
        return datetime.now().year

    @property
    def _current_month(self) -> str:
        return datetime.now().strftime("%B")

    @property
    def _current_week(self) -> str:
        # Get week of month (1st, 2nd, etc.)
        day = datetime.now().day
        if day <= 7:
            return "first week"
        elif day <= 14:
            return "second week"
        elif day <= 21:
            return "third week"
        else:
            return "last week"

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
                "companion_type": "movie recommendation expert",
                "content_name": "movie",
                "content_plural": "movies",
                "date_description": "release year",
                "type_label": "movie",
            },
            ContentType.SERIES: {
                "companion_type": "TV series recommendation expert",
                "content_name": "TV series",
                "content_plural": "TV series",
                "date_description": "first air year",
                "type_label": "series",
            },
        }
        instructions = base_instructions[content_type]
        current_year = self._current_year
        current_month = self._current_month
        current_week = self._current_week

        system_prompt = f"""You are a {instructions['companion_type']}. Today is {self._current_date} ({current_week} of {current_month}).

You will provide structured {instructions['content_name']} recommendations with the following fields:
- title: The exact {instructions['content_name']} title (without year)
- year: The {instructions['date_description']} as an integer
- streaming_platform: The primary streaming platform if known (optional)
- note: Additional context like "New this week", "Trending", etc. (optional)

CRITICAL INSTRUCTION FOR STREAMING/CURRENT CONTENT QUERIES:
If the user asks about:
- What's new on streaming services (Netflix, Prime Video, Hulu, Disney+, Max, Apple TV+, etc.)
- What's trending this week/month
- New releases on streaming platforms
- What's coming to streaming services
- Current streaming content

YOU MUST:
1. Use web search to find current information (your training data is outdated for this)
2. Focus on {instructions['content_plural']} actually available NOW on major streaming services
3. Include the streaming_platform field when known
4. Add relevant notes like "New this week", "Trending #1", etc.
5. Prioritize streaming availability over theatrical or physical releases

QUERY ANALYSIS INSTRUCTIONS:
1. Identify the type of query:
   - STREAMING/CURRENT QUERIES (requires web search):
     * "what's new on Netflix/streaming this week/month"
     * "trending on streaming services"
     * "new releases on [platform]"
     * "what's coming to streaming in [month]"
   - Specific {instructions['content_name']} (e.g., "The Matrix", "Breaking Bad")
   - Franchise/series query (e.g., "Mission Impossible movies", "Star Wars films")
   - Actor/Director filmography (e.g., "Tom Cruise movies", "Christopher Nolan films")
   - Genre-based recommendations (e.g., "sci-fi movies", "crime dramas")
   - Mood/theme-based recommendations (e.g., "feel-good movies", "dark psychological thrillers")
   - Time-based queries (e.g., "movies from the 80s", "recent releases")
   - General recommendations (e.g., "something good to watch")

TIME-BASED QUERY HANDLING:
- Current year is {current_year}
- Current month is {current_month}
- "this week" = current week ({current_week} of {current_month} {current_year})
- "this month" = {current_month} {current_year}
- "past year" or "last year" = {current_year - 1} to {current_year}
- "recent" or "recently" = {current_year - 3} to {current_year}
- "new" or "latest" = {current_year} (or current month for streaming queries)
- "2020s" = 2020 to {current_year}
- "last decade" = {current_year - 10} to {current_year}

RECOMMENDATION STRATEGIES:

For STREAMING/CURRENT CONTENT queries:
- MUST use web search to get up-to-date information
- Always populate the streaming_platform field
- Add contextual notes (e.g., "Netflix Original", "New this week")
- Mix new originals with newly added catalog titles
- Consider trending or popular content on platforms

For SPECIFIC {instructions['content_name'].upper()} queries:
- Return only that exact {instructions['content_name']} and its direct sequels/prequels
- Include year for each entry
- Add notes for sequels (e.g., "Sequel", "Part 2")

For FRANCHISE queries:
- List all official entries with their respective years
- Add notes for chronological order if different from release order
- Include streaming_platform if consistently available

For ACTOR/DIRECTOR queries:
- Provide diverse selections with accurate years
- Note special roles (e.g., "Directorial debut", "Oscar-winning performance")

For GENRE/MOOD recommendations:
- Match the specific mood or tone requested
- Include a variety of years to show range
- Note relevant accolades or special features

CRITICAL REQUIREMENTS:
- You MUST return exactly {max_results} {instructions['content_plural']}
- Each entry MUST have a title (string) and year (integer)
- The year must be accurate - this is critical for identification
- For streaming queries, use web search to ensure current information
- Include streaming_platform when known
- Add helpful notes when they provide value
- Never include the year in the title field - it must be separate

ORDERING PRINCIPLES:
- For streaming queries: newest additions or most popular first
- For specific queries: chronological or series order
- For quality-based queries: highest rated first
- For time-based queries: most recent first or chronological
- For genre/mood queries: best matches first

Remember:
- The structured format allows for better data handling
- Always provide accurate years as integers
- Use the optional fields (streaming_platform, note) to enhance recommendations
- For current streaming content, web search is ESSENTIAL"""

        user_prompt = f"""Generate exactly {max_results} {instructions['content_plural']} recommendations for this query: "{query}"

Provide your response as structured data with separate title and year fields.
If this is about current streaming content, use web search for accurate information and include the streaming platform."""

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
    ) -> List[Union[MovieSuggestion, TVSeriesSuggestion]]:
        """
        Attempt to get structured completion from OpenAI using .parse().
        Returns a list of structured suggestion objects.
        """
        self.logger.debug(f"Attempting Structured Output with model '{self.model}'")

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
    ) -> List[Union[MovieSuggestion, TVSeriesSuggestion]]:
        """
        Attempt fallback using JSON Mode.
        Returns a list of structured suggestion objects.
        """
        self.logger.warning("Falling back to JSON Mode.")

        # Add a final instruction to the messages to strongly request JSON.
        messages_with_fallback = messages + [
            {
                "role": "system",
                "content": f"You must respond with a valid JSON object that conforms to this schema: {json.dumps(response_model.model_json_schema())}. Do not include the schema in your response!",
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

    async def _generate_suggestions(
        self, query: str, max_results: int, *, content_type: ContentType
    ) -> List[Union[MovieSuggestion, TVSeriesSuggestion]]:
        """
        Generate content suggestions, prioritizing Structured Outputs and then
        falling back to JSON mode if necessary.

        Returns a list of Pydantic model objects (MovieSuggestion or TVSeriesSuggestion).
        """
        self.logger.debug(f"Generating {max_results} {content_type.value} suggestions for query: '{query}'")

        messages = self._build_messages(query, max_results, content_type)
        response_model, field_name = self._get_response_config(content_type)

        try:
            suggestions = await self._try_structured_completion(messages, response_model, field_name, max_results)
            return suggestions
        except (openai.BadRequestError, AttributeError) as e:
            self.logger.warning(f"Structured Output (.parse) failed: {e}. Attempting fallback.")
            try:
                suggestions = await self._try_fallback_completion(messages, response_model, field_name, max_results)
                return suggestions
            except Exception as fallback_e:
                self.logger.error(f"Fallback completion also failed: {fallback_e}")
                # Return a fallback suggestion as a Pydantic model
                if content_type == ContentType.MOVIE:
                    return [MovieSuggestion(title=query, year=2024)]
                else:
                    return [TVSeriesSuggestion(title=query, year=2024)]
        except Exception as e:
            self.logger.error(f"An unexpected LLM service error occurred: {e}")
            # Return a fallback suggestion as a Pydantic model
            if content_type == ContentType.MOVIE:
                return [MovieSuggestion(title=query, year=2024)]
            else:
                return [TVSeriesSuggestion(title=query, year=2024)]

    def _filter_duplicates(
        self, suggestions: List[Union[MovieSuggestion, TVSeriesSuggestion]]
    ) -> List[Union[MovieSuggestion, TVSeriesSuggestion]]:
        """
        Filter out duplicate suggestions based on title and year.

        Args:
            suggestions: List of movie or TV series suggestions

        Returns:
            List with duplicates removed, preserving order
        """
        seen = set()
        filtered = []

        for suggestion in suggestions:
            # Create a unique key based on normalized title and year
            key = (suggestion.title.lower().strip(), suggestion.year)
            if key not in seen:
                seen.add(key)
                filtered.append(suggestion)

        return filtered

    async def generate_movie_suggestions(self, query: str, max_results: int) -> List[MovieSuggestion]:
        """Generate movie suggestions and return as Pydantic models."""
        suggestions = await self._generate_suggestions(query, max_results, content_type=ContentType.MOVIE)
        filtered_suggestions = self._filter_duplicates(suggestions)
        return cast(List[MovieSuggestion], filtered_suggestions)

    async def generate_tv_suggestions(self, query: str, max_results: int) -> List[TVSeriesSuggestion]:
        """Generate TV series suggestions and return as Pydantic models."""
        suggestions = await self._generate_suggestions(query, max_results, content_type=ContentType.SERIES)
        filtered_suggestions = self._filter_duplicates(suggestions)
        return cast(List[TVSeriesSuggestion], filtered_suggestions)
