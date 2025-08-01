"""
LLM service for the Stremio AI Companion application.
"""

import json
import logging
from datetime import datetime
from typing import List

import openai

from app.models.config import Config
from app.models.movie import MovieSuggestions, TVSeriesSuggestions


class LLMService:
    """
    Service for generating movie suggestions using OpenAI's LLM.

    This service handles communication with the OpenAI API to generate
    movie suggestions based on user queries.
    """

    def __init__(self, config: Config):
        """
        Initialize the LLM service with configuration.

        Args:
            config: Configuration object with OpenAI settings
        """
        self.client = openai.AsyncOpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url)
        self.model = config.model_name
        self.logger = logging.getLogger("stremio_ai_companion.LLMService")

    async def generate_movie_suggestions(self, query: str, max_results: int) -> List[str]:
        """
        Generate movie suggestions based on a user query.

        Args:
            query: The user's search query
            max_results: Maximum number of movie suggestions to return

        Returns:
            List of movie titles with years
        """
        self.logger.debug(f"Generating {max_results} movie suggestions for query: '{query}'")

        # Get current date for context
        current_date = datetime.now().strftime("%B %Y")

        prompt = f"""You are a movie discovery AI companion. Today is {current_date}. Generate {max_results} movie titles that perfectly match this search query: "{query}"

Focus on understanding the user's mood, preferences, and context. If they mention themes, genres, time periods, or specific feelings they want to experience, find movies that truly capture those elements.

IMPORTANT: Return each movie title with its release year in parentheses, like "Movie Title (YYYY)". This helps with accurate movie identification.

Each title must be a real movie that exists and genuinely matches the user's request."""

        try:
            # Try structured output first
            try:
                response = await self.client.chat.completions.parse(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=MovieSuggestions,
                    temperature=0.7,
                    max_tokens=5000,
                    timeout=30,
                )

                if response.choices[0].message.parsed:
                    movies = response.choices[0].message.parsed.movies
                    self.logger.debug(f"Successfully parsed {len(movies)} movies using structured output")
                    return movies[:max_results]
                else:
                    # Fall back to refusal handling or regular completion
                    self.logger.warning("Structured output parsing failed, falling back to regular completion")
                    raise Exception("Structured output parsing failed")

            except (AttributeError, openai.BadRequestError) as e:
                # Model doesn't support structured output, fall back to regular completion
                self.logger.warning(f"Structured output not supported, falling back to regular completion: {e}")

                fallback_prompt = f"""{prompt}

Return only a JSON array of movie titles, nothing else.
Example format: ["Movie Title 1", "Movie Title 2", "Movie Title 3"]

Query: {query}"""

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": fallback_prompt}],
                    temperature=0.7,
                    max_tokens=5000,
                    timeout=30,
                )

                content = response.choices[0].message.content.strip()

                # Clean up JSON formatting
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()

                movies = json.loads(content)
                if isinstance(movies, list) and all(isinstance(movie, str) for movie in movies):
                    self.logger.debug(f"Successfully parsed {len(movies)} movies from fallback completion")
                    return movies[:max_results]
                else:
                    self.logger.warning("Invalid movie list format from LLM, returning query as fallback")
                    return [query]

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}, returning fallback")
            return [query]
        except openai.APIError as e:
            self.logger.error(f"OpenAI API error: {e}")
            return [query]
        except Exception as e:
            self.logger.error(f"LLM service error: {e}")
            return [query]

    async def generate_tv_suggestions(self, query: str, max_results: int) -> List[str]:
        """
        Generate TV series suggestions based on a user query.

        Args:
            query: The user's search query
            max_results: Maximum number of TV series suggestions to return

        Returns:
            List of TV series titles with years
        """
        self.logger.debug(f"Generating {max_results} TV series suggestions for query: '{query}'")

        # Get current date for context
        current_date = datetime.now().strftime("%B %Y")

        prompt = f"""You are a TV series discovery AI companion. Today is {current_date}. Generate {max_results} TV series titles that perfectly match this search query: "{query}"

Focus on understanding the user's mood, preferences, and context. If they mention themes, genres, time periods, or specific feelings they want to experience, find TV series that truly capture those elements.

IMPORTANT: Return each TV series title with its first air year in parentheses, like "Series Title (YYYY)". This helps with accurate series identification.

Each title must be a real TV series that exists and genuinely matches the user's request."""

        try:
            # Try structured output first
            try:
                response = await self.client.chat.completions.parse(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=TVSeriesSuggestions,
                    temperature=0.7,
                    max_tokens=5000,
                    timeout=30,
                )

                if response.choices[0].message.parsed:
                    series = response.choices[0].message.parsed.series
                    self.logger.debug(f"Successfully parsed {len(series)} TV series using structured output")
                    return series[:max_results]
                else:
                    # Fall back to refusal handling or regular completion
                    self.logger.warning("Structured output parsing failed, falling back to regular completion")
                    raise Exception("Structured output parsing failed")

            except (AttributeError, openai.BadRequestError) as e:
                # Model doesn't support structured output, fall back to regular completion
                self.logger.warning(f"Structured output not supported, falling back to regular completion: {e}")

                fallback_prompt = f"""{prompt}

Return only a JSON array of TV series titles, nothing else.
Example format: ["Series Title 1", "Series Title 2", "Series Title 3"]

Query: {query}"""

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": fallback_prompt}],
                    temperature=0.7,
                    max_tokens=5000,
                    timeout=30,
                )

                content = response.choices[0].message.content.strip()

                # Clean up JSON formatting
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "").strip()
                elif content.startswith("```"):
                    content = content.replace("```", "").strip()

                series = json.loads(content)
                if isinstance(series, list) and all(isinstance(show, str) for show in series):
                    self.logger.debug(f"Successfully parsed {len(series)} TV series from fallback completion")
                    return series[:max_results]
                else:
                    self.logger.warning("Invalid TV series list format from LLM, returning query as fallback")
                    return [query]

        except json.JSONDecodeError as e:
            self.logger.error(f"JSON decode error: {e}, returning fallback")
            return [query]
        except openai.APIError as e:
            self.logger.error(f"OpenAI API error: {e}")
            return [query]
        except Exception as e:
            self.logger.error(f"LLM service error: {e}")
            return [query]
