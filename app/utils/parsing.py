"""
Parsing utilities for the Stremio AI Companion application.
"""

import re
from typing import Tuple, Optional

def parse_query_with_year(query: str) -> Tuple[str, Optional[int]]:
    """
    Parse a query to extract movie title and optional year.
    
    Args:
        query: The search query string
        
    Returns:
        A tuple containing the movie title and optional year
        
    Examples:
        - "twins (1988)" -> ("twins", 1988)
        - "twins" -> ("twins", None)
        - "The Matrix (1999)" -> ("The Matrix", 1999)
    """
    # Pattern to match year in parentheses at the end
    year_pattern = r'\s*\((\d{4})\)\s*$'
    match = re.search(year_pattern, query)
    
    if match:
        year = int(match.group(1))
        title = re.sub(year_pattern, '', query).strip()
        return title, year
    
    return query.strip(), None

def parse_movie_with_year(movie_title: str) -> Tuple[str, Optional[int]]:
    """
    Parse a movie title from LLM response to extract title and year.
    
    Args:
        movie_title: The movie title string, possibly with year in parentheses
        
    Returns:
        A tuple containing the movie title and optional year
        
    Examples:
        - "The Matrix (1999)" -> ("The Matrix", 1999)
        - "Inception (2010)" -> ("Inception", 2010)
        - "Some Movie" -> ("Some Movie", None)
    """
    # Pattern to match year in parentheses
    year_pattern = r'\s*\((\d{4})\)\s*$'
    match = re.search(year_pattern, movie_title)
    
    if match:
        year = int(match.group(1))
        title = re.sub(year_pattern, '', movie_title).strip()
        return title, year
    
    return movie_title.strip(), None