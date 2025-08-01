from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import json
import base64
import os
import logging
import sys
import re
from typing import List, Dict, Any, Optional, Tuple
from pydantic import BaseModel, validator, ValidationError, ConfigDict, Field
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import openai

# Configure logging
def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration with specified level"""
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific logger levels
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

# Initialize logging with environment variable or default to INFO
log_level = os.getenv("LOG_LEVEL", "INFO")
logger = setup_logging(log_level)

app = FastAPI(title="Stremio AI Companion", description="Your AI-powered movie discovery companion for Stremio")

# Add request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"{request.method} {request.url} - Headers: {dict(request.headers)}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

templates = Jinja2Templates(directory="templates")

class Config(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    openai_api_key: str
    openai_base_url: Optional[str] = "https://api.openai.com/v1"
    model_name: str = "gpt-4.1-mini"
    tmdb_read_access_token: str
    max_results: int = 20
    include_adult: bool = False
    use_posterdb: bool = False
    posterdb_api_key: Optional[str] = None
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('OpenAI API key must be provided and valid')
        return v.strip()
    
    @validator('tmdb_read_access_token')
    def validate_tmdb_token(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('TMDB read access token must be provided and valid')
        return v.strip()
    
    @validator('max_results')
    def validate_max_results(cls, v):
        if v < 1 or v > 50:
            raise ValueError('Max results must be between 1 and 50')
        return v
    
    @validator('openai_base_url')
    def validate_openai_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('OpenAI base URL must be a valid HTTP/HTTPS URL')
        return v
    
    @validator('posterdb_api_key')
    def validate_posterdb_key(cls, v, values):
        if values.get('use_posterdb') and (not v or len(v.strip()) < 5):
            raise ValueError('RPDB API key is required when RPDB is enabled')
        return v.strip() if v else None

class EncryptionService:
    def __init__(self, password: str = "stremio-ai-companion-default-key"):
        self.password = password.encode()
        
    def _get_key(self, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.password))
    
    def encrypt(self, data: str) -> str:
        salt = os.urandom(16)
        key = self._get_key(salt)
        f = Fernet(key)
        encrypted = f.encrypt(data.encode())
        return base64.urlsafe_b64encode(salt + encrypted).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        try:
            data = base64.urlsafe_b64decode(encrypted_data.encode())
            salt = data[:16]
            encrypted = data[16:]
            key = self._get_key(salt)
            f = Fernet(key)
            return f.decrypt(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt config data: {e}")
            raise HTTPException(status_code=400, detail="Invalid config data")

encryption_service = EncryptionService(os.getenv("STREMIO_AI_ENCRYPTION_KEY", "stremio-ai-companion-default-key"))

def parse_query_with_year(query: str) -> Tuple[str, Optional[int]]:
    """
    Parse a query to extract movie title and optional year.
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

class MovieSuggestions(BaseModel):
    """Pydantic model for structured movie suggestions output"""
    movies: List[str] = Field(description="List of movie titles that match the search query")
    
    @validator('movies')
    def validate_movies(cls, v):
        if not v or len(v) == 0:
            raise ValueError('At least one movie suggestion is required')
        return v

class LLMService:
    def __init__(self, config: Config):
        self.client = openai.OpenAI(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url
        )
        self.model = config.model_name
        self.logger = logging.getLogger(f"{__name__}.LLMService")
    
    async def generate_movie_suggestions(self, query: str, max_results: int) -> List[str]:
        self.logger.info(f"Generating {max_results} movie suggestions for query: '{query}'")
        
        # Parse query to extract title and year (for specific movie searches like "twins (1988)")
        title, year = parse_query_with_year(query)
        
        # If year is specified in the query, focus on that specific movie
        if year:
            prompt = f"""You are a movie discovery AI companion. The user is searching for the movie "{title}" from {year}.

Return the exact title of this movie as it appears in movie databases, followed by similar movies from around the same time period or with similar themes.

Return each movie title with its release year in parentheses, like "Movie Title (YYYY)".

Generate {max_results} movie titles total, starting with the specific movie requested."""
        else:
            prompt = f"""You are a movie discovery AI companion. Generate {max_results} movie titles that perfectly match this search query: "{query}"

Focus on understanding the user's mood, preferences, and context. If they mention themes, genres, time periods, or specific feelings they want to experience, find movies that truly capture those elements.

IMPORTANT: Return each movie title with its release year in parentheses, like "Movie Title (YYYY)". This helps with accurate movie identification.

Each title should be a real movie that exists and genuinely matches the user's request."""
        
        try:
            # Try structured output first
            try:
                response = self.client.beta.chat.completions.parse(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    response_format=MovieSuggestions,
                    temperature=0.7,
                    max_tokens=500,
                    timeout=30
                )
                
                if response.choices[0].message.parsed:
                    movies = response.choices[0].message.parsed.movies
                    self.logger.info(f"Successfully parsed {len(movies)} movies using structured output")
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
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": fallback_prompt}],
                    temperature=0.7,
                    max_tokens=500,
                    timeout=30
                )
                
                content = response.choices[0].message.content.strip()
                
                # Clean up JSON formatting
                if content.startswith('```json'):
                    content = content.replace('```json', '').replace('```', '').strip()
                elif content.startswith('```'):
                    content = content.replace('```', '').strip()
                
                movies = json.loads(content)
                if isinstance(movies, list) and all(isinstance(movie, str) for movie in movies):
                    self.logger.info(f"Successfully parsed {len(movies)} movies from fallback completion")
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

class TMDBService:
    def __init__(self, read_access_token: str):
        self.read_access_token = read_access_token
        self.base_url = "https://api.themoviedb.org/3"
        self.logger = logging.getLogger(f"{__name__}.TMDBService")
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "accept": "application/json",
            "Authorization": f"Bearer {self.read_access_token}"
        }
    
    async def search_movie(self, title: str, year: Optional[int] = None, include_adult: bool = False) -> Optional[Dict[str, Any]]:
        self.logger.info(f"Searching TMDB for movie: '{title}'" + (f" ({year})" if year else ""))
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                params = {
                    "query": title,
                    "include_adult": "true" if include_adult else "false",
                    "language": "en-US",
                    "page": "1"
                }
                
                # Add year filter if provided
                if year:
                    params["primary_release_year"] = str(year)
                
                response = await client.get(
                    f"{self.base_url}/search/movie",
                    params=params,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                data = response.json()
                
                if response.status_code == 401:
                    self.logger.error("TMDB API authentication failed - check read access token")
                    return None
                
                if data.get("results"):
                    result = data["results"][0]
                    self.logger.info(f"Found TMDB result for '{title}': {result.get('title', 'Unknown')} ({result.get('release_date', 'Unknown')[:4] if result.get('release_date') else 'Unknown'})")
                    return result
                else:
                    self.logger.warning(f"No TMDB results found for '{title}'" + (f" ({year})" if year else ""))
                return None
            except httpx.TimeoutException:
                self.logger.warning(f"TMDB search timeout for: {title}")
                return None
            except httpx.HTTPStatusError as e:
                self.logger.error(f"TMDB HTTP error {e.response.status_code} for: {title}")
                return None
            except Exception as e:
                self.logger.error(f"TMDB search error for {title}: {e}")
                return None
    
    async def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        self.logger.info(f"Fetching TMDB details for movie ID: {movie_id}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                params = {
                    "language": "en-US",
                    "append_to_response": "external_ids"  # This includes IMDB ID
                }
                
                response = await client.get(
                    f"{self.base_url}/movie/{movie_id}",
                    params=params,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                details = response.json()
                self.logger.info(f"Successfully fetched details for movie ID {movie_id}: {details.get('title', 'Unknown')}")
                return details
            except httpx.TimeoutException:
                self.logger.warning(f"TMDB details timeout for movie ID: {movie_id}")
                return None
            except httpx.HTTPStatusError as e:
                self.logger.error(f"TMDB HTTP error {e.response.status_code} for movie ID: {movie_id}")
                return None
            except Exception as e:
                self.logger.error(f"TMDB details error for movie ID {movie_id}: {e}")
                return None

class RPDBService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.logger = logging.getLogger(f"{__name__}.RPDBService")
    
    async def get_poster(self, imdb_id: str) -> Optional[str]:
        if not self.api_key or not imdb_id:
            self.logger.info("RPDB API key or IMDB ID not provided")
            return None
        
        try:
            # RPDB uses direct image URLs with the API key
            # Format: https://api.ratingposterdb.com/{api_key}/imdb/poster-default/{imdb_id}.jpg
            # Ensure IMDB ID has 'tt' prefix
            if not imdb_id.startswith('tt'):
                imdb_id = f"tt{imdb_id}"
            
            poster_url = f"https://api.ratingposterdb.com/{self.api_key}/imdb/poster-default/{imdb_id}.jpg"
            
            # For valid API keys, we can return the URL directly without testing
            # The image will load if it exists, or show broken image if not
            self.logger.info(f"Generated RPDB poster URL for {imdb_id}")
            return poster_url
                    
        except Exception as e:
            self.logger.error(f"RPDB error for IMDB ID {imdb_id}: {e}")
            return None

def movie_to_stremio_meta(movie: Dict[str, Any], poster_url: Optional[str] = None) -> Dict[str, Any]:
    tmdb_poster = f"https://image.tmdb.org/t/p/w500{movie.get('poster_path', '')}" if movie.get('poster_path') else None
    
    return {
        "id": f"tmdb:{movie.get('id')}",
        "type": "movie",
        "name": movie.get("title", "Unknown"),
        "poster": poster_url or tmdb_poster,
        "background": f"https://image.tmdb.org/t/p/w1280{movie.get('backdrop_path', '')}" if movie.get('backdrop_path') else None,
        "description": movie.get("overview", ""),
        "releaseInfo": movie.get("release_date", "").split("-")[0] if movie.get("release_date") else None,
        "imdbRating": movie.get("vote_average"),
        "genre": [genre["name"] for genre in movie.get("genres", [])] if movie.get("genres") else None,
        "runtime": f"{movie.get('runtime', 0)} min" if movie.get("runtime") else None
    }

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/configure", response_class=HTMLResponse)
async def configure_page(request: Request, config: Optional[str] = Query(None)):
    existing_config = None
    if config:
        try:
            config_data = encryption_service.decrypt(config)
            existing_config = Config.model_validate(json.loads(config_data))
        except Exception as e:
            # If config is invalid, just show empty form
            logger.warning(f"Invalid config provided to configure page: {e}")
            pass
    
    return templates.TemplateResponse("configure.html", {
        "request": request,
        "existing_config": existing_config
    })



@app.get("/config/{config}/debug")
async def debug_config(config: str):
    """Debug endpoint to help troubleshoot config issues"""
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))
        return {
            "status": "valid",
            "config_length": len(config),
            "decrypted_length": len(config_data),
            "config_summary": {
                "openai_base_url": config_obj.openai_base_url,
                "model_name": config_obj.model_name,
                "max_results": config_obj.max_results,
                "use_posterdb": config_obj.use_posterdb
            }
        }
    except Exception as e:
        return {
            "status": "invalid",
            "error": str(e),
            "config_length": len(config)
        }

@app.get("/config/{config}/preview", response_class=HTMLResponse)
async def preview_page(request: Request, config: str):
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))
        manifest_url = f"{request.url.scheme}://{request.url.netloc}/config/{config}/manifest.json"
        return templates.TemplateResponse("preview.html", {
            "request": request,
            "manifest_url": manifest_url,
            "config": config_obj
        })
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in preview: {e}")
        raise HTTPException(status_code=400, detail="Invalid config format")
    except ValidationError as e:
        logger.error(f"Validation error in preview: {e}")
        raise HTTPException(status_code=400, detail="Invalid config data")
    except Exception as e:
        logger.error(f"General error in preview: {e}")
        raise HTTPException(status_code=400, detail=f"Config error: {str(e)}")

@app.post("/save-config")
async def save_config(
    request: Request,
    openai_api_key: str = Form(...),
    openai_base_url: str = Form("https://api.openai.com/v1"),
    model_name: str = Form("gpt-4.1-mini"),
    tmdb_read_access_token: str = Form(...),
    max_results: int = Form(20),
    include_adult: Optional[str] = Form(None),
    use_posterdb: Optional[str] = Form(None),
    posterdb_api_key: str = Form("")
):
    try:
        # Handle checkboxes: if not present in form data, it means False
        include_adult_bool = include_adult == "on" if include_adult else False
        use_posterdb_bool = use_posterdb == "on" if use_posterdb else False
        
        config = Config(
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            model_name=model_name,
            tmdb_read_access_token=tmdb_read_access_token,
            max_results=max_results,
            include_adult=include_adult_bool,
            use_posterdb=use_posterdb_bool,
            posterdb_api_key=posterdb_api_key if posterdb_api_key else None
        )
        
        encrypted_config = encryption_service.encrypt(config.model_dump_json())
        manifest_url = f"{request.url.scheme}://{request.url.netloc}/config/{encrypted_config}/manifest.json"
        
        return JSONResponse({
            "success": True,
            "manifest_url": manifest_url,
            "preview_url": f"{request.url.scheme}://{request.url.netloc}/config/{encrypted_config}/preview"
        })
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            field = error['loc'][-1] if error['loc'] else 'unknown'
            message = error['msg']
            error_messages.append(f"{field}: {message}")
        
        return JSONResponse({
            "success": False,
            "detail": "Validation failed: " + "; ".join(error_messages)
        }, status_code=400)
    except Exception as e:
        return JSONResponse({
            "success": False,
            "detail": f"Configuration error: {str(e)}"
        }, status_code=500)

@app.get("/config/{config}")
async def config_redirect(config: str):
    """Redirect to configure page with existing config"""
    return RedirectResponse(url=f"/configure?config={config}")

@app.get("/config/{config}/manifest.json")
async def get_manifest(config: str):
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))
        
        return {
            "id": "ai.companion.stremio",
            "version": "0.0.1",
            "name": "AI Companion",
            "description": "Your AI-powered movie discovery companion",
            "logo": "https://raw.githubusercontent.com/willtho89/stremio-ai-companion/refs/heads/main/.assets/logo2_256.png",
            "resources": ["catalog"],
            "types": ["movie"],
            "catalogs": [{
                "type": "movie",
                "id": "ai_companion_movie",
                "name": "AI Movie Discovery",
                "extra": [{"name": "search", "isRequired": True}]
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid config")

async def _process_catalog_request(config: str, catalog_id: str, search: str):
    """Shared catalog processing logic"""
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))

        logger.info(f"Processing catalog request for '{search}' with {config_obj.max_results} max results")
        
        llm_service = LLMService(config_obj)
        tmdb_service = TMDBService(config_obj.tmdb_read_access_token)
        rpdb_service = RPDBService(config_obj.posterdb_api_key) if config_obj.use_posterdb else None
        
        # Parse the search query to extract title and year
        if not search:
            search = "Give me some movies you think are must sees"
        
        movie_titles = await llm_service.generate_movie_suggestions(search, config_obj.max_results)
        logger.info(f"Generated {len(movie_titles)} movie suggestions: {movie_titles}")
        
        tasks = []
        for i, movie_title in enumerate(movie_titles):
            # Parse each movie title to extract title and year from LLM response
            title, movie_year = parse_movie_with_year(movie_title)
            
            # Use the year from the movie title if available, otherwise use search year for first result
            year_filter = movie_year or (search_year if (i == 0 and search_year) else None)
            
            tasks.append(tmdb_service.search_movie(title, year_filter, config_obj.include_adult))
        
        tmdb_results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Completed TMDB searches for {len(tmdb_results)} movies")
        
        # Get movie details for all valid results concurrently
        detail_tasks = []
        valid_results = []
        for result in tmdb_results:
            if isinstance(result, dict) and result:
                detail_tasks.append(tmdb_service.get_movie_details(result["id"]))
                valid_results.append(result)
        
        movie_details_list = await asyncio.gather(*detail_tasks, return_exceptions=True)
        
        # Collect IMDB IDs for RPDB poster fetching
        poster_tasks = []
        movie_details_with_imdb = []
        
        for movie_details in movie_details_list:
            if isinstance(movie_details, dict) and movie_details:
                movie_details_with_imdb.append(movie_details)
                if rpdb_service:
                    imdb_id = movie_details.get("external_ids", {}).get("imdb_id")
                    if imdb_id:
                        poster_tasks.append(rpdb_service.get_poster(imdb_id))
                    else:
                        poster_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
                else:
                    poster_tasks.append(asyncio.create_task(asyncio.sleep(0, result=None)))
        
        # Fetch all RPDB posters concurrently
        poster_urls = await asyncio.gather(*poster_tasks, return_exceptions=True) if poster_tasks else []
        
        # Build final metadata
        metas = []
        for i, movie_details in enumerate(movie_details_with_imdb):
            poster_url = None
            if i < len(poster_urls) and isinstance(poster_urls[i], str):
                poster_url = poster_urls[i]
            
            meta = movie_to_stremio_meta(movie_details, poster_url)
            metas.append(meta)
        
        logger.info(f"Returning {len(metas)} movie metadata entries")
        return {"metas": metas}
        
    except Exception as e:
        logger.error(f"Catalog request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/{config}/catalog/movie/{catalog_id}.json")
async def get_catalog(config: str, catalog_id: str, search: str | None = Query(default=None)):
    """Path-based catalog endpoint"""
    return await _process_catalog_request(config, catalog_id, search)

@app.get("/config/{config}/catalog/movie/{catalog_id}/search={search}.json")
async def get_catalog(config: str, catalog_id: str, search: str):
    """Path-based catalog endpoint"""
    return await _process_catalog_request(config, catalog_id, search)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)