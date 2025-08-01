from fastapi import FastAPI, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import httpx
import asyncio
import json
import base64
import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, validator, ValidationError, ConfigDict, Field
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import openai

app = FastAPI(title="Stremio AI Companion", description="Your AI-powered movie discovery companion for Stremio")

templates = Jinja2Templates(directory="templates")

class Config(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    
    openai_api_key: str
    openai_base_url: Optional[str] = "https://api.openai.com/v1"
    model_name: str = "gpt-4.1-mini"
    tmdb_api_key: str
    max_results: int = 20
    use_posterdb: bool = False
    posterdb_api_key: Optional[str] = None
    
    @validator('openai_api_key')
    def validate_openai_key(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('OpenAI API key must be provided and valid')
        return v.strip()
    
    @validator('tmdb_api_key')
    def validate_tmdb_key(cls, v):
        if not v or len(v.strip()) < 10:
            raise ValueError('TMDB API key must be provided and valid')
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
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid config data")

encryption_service = EncryptionService(os.getenv("STREMIO_AI_ENCRYPTION_KEY", "stremio-ai-companion-default-key"))

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
    
    async def generate_movie_suggestions(self, query: str, max_results: int) -> List[str]:
        prompt = f"""You are a movie discovery AI companion. Generate {max_results} movie titles that perfectly match this search query: "{query}"

Focus on understanding the user's mood, preferences, and context. If they mention themes, genres, time periods, or specific feelings they want to experience, find movies that truly capture those elements.

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
                    return movies[:max_results]
                else:
                    # Fall back to refusal handling or regular completion
                    raise Exception("Structured output parsing failed")
                    
            except (AttributeError, openai.BadRequestError) as e:
                # Model doesn't support structured output, fall back to regular completion
                print(f"Structured output not supported, falling back to regular completion: {e}")
                
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
                    return movies[:max_results]
                else:
                    return [query]
                    
        except json.JSONDecodeError:
            print(f"JSON decode error, returning fallback")
            return [query]
        except openai.APIError as e:
            print(f"OpenAI API error: {e}")
            return [query]
        except Exception as e:
            print(f"LLM service error: {e}")
            return [query]

class TMDBService:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.themoviedb.org/3"
    
    async def search_movie(self, title: str) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/search/movie",
                    params={
                        "api_key": self.api_key,
                        "query": title,
                        "language": "en-US"
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                if response.status_code == 401:
                    print(f"TMDB API authentication failed - check API key")
                    return None
                
                if data.get("results"):
                    return data["results"][0]
                return None
            except httpx.TimeoutException:
                print(f"TMDB search timeout for: {title}")
                return None
            except httpx.HTTPStatusError as e:
                print(f"TMDB HTTP error {e.response.status_code} for: {title}")
                return None
            except Exception as e:
                print(f"TMDB search error for {title}: {e}")
                return None
    
    async def get_movie_details(self, movie_id: int) -> Optional[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(
                    f"{self.base_url}/movie/{movie_id}",
                    params={
                        "api_key": self.api_key,
                        "language": "en-US",
                        "append_to_response": "external_ids"  # This includes IMDB ID
                    }
                )
                response.raise_for_status()
                return response.json()
            except httpx.TimeoutException:
                print(f"TMDB details timeout for movie ID: {movie_id}")
                return None
            except httpx.HTTPStatusError as e:
                print(f"TMDB HTTP error {e.response.status_code} for movie ID: {movie_id}")
                return None
            except Exception as e:
                print(f"TMDB details error for movie ID {movie_id}: {e}")
                return None

class RPDBService:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    async def get_poster(self, imdb_id: str) -> Optional[str]:
        if not self.api_key or not imdb_id:
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
            print(f"🎬 RPDB poster URL generated for {imdb_id}")
            return poster_url
                    
        except Exception as e:
            print(f"RPDB error for IMDB ID {imdb_id}: {e}")
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
        except Exception:
            # If config is invalid, just show empty form
            pass
    
    return templates.TemplateResponse("configure.html", {
        "request": request,
        "existing_config": existing_config
    })



@app.get("/debug-config")
async def debug_config(config: str = Query(...)):
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

@app.get("/preview", response_class=HTMLResponse)
async def preview_page(request: Request, config: str = Query(...)):
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))
        manifest_url = f"{request.url.scheme}://{request.url.netloc}/manifest.json?config={config}"
        return templates.TemplateResponse("preview.html", {
            "request": request,
            "manifest_url": manifest_url,
            "config": config_obj
        })
    except json.JSONDecodeError as e:
        print(f"JSON decode error in preview: {e}")
        raise HTTPException(status_code=400, detail="Invalid config format")
    except ValidationError as e:
        print(f"Validation error in preview: {e}")
        raise HTTPException(status_code=400, detail="Invalid config data")
    except Exception as e:
        print(f"General error in preview: {e}")
        raise HTTPException(status_code=400, detail=f"Config error: {str(e)}")

@app.post("/save-config")
async def save_config(
    request: Request,
    openai_api_key: str = Form(...),
    openai_base_url: str = Form("https://api.openai.com/v1"),
    model_name: str = Form("gpt-3.5-turbo"),
    tmdb_api_key: str = Form(...),
    max_results: int = Form(20),
    use_posterdb: Optional[str] = Form(None),
    posterdb_api_key: str = Form("")
):
    try:
        # Handle checkbox: if not present in form data, it means False
        use_posterdb_bool = use_posterdb == "on" if use_posterdb else False
        
        config = Config(
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
            model_name=model_name,
            tmdb_api_key=tmdb_api_key,
            max_results=max_results,
            use_posterdb=use_posterdb_bool,
            posterdb_api_key=posterdb_api_key if posterdb_api_key else None
        )
        
        encrypted_config = encryption_service.encrypt(config.model_dump_json())
        manifest_url = f"{request.url.scheme}://{request.url.netloc}/manifest.json?config={encrypted_config}"
        
        return JSONResponse({
            "success": True,
            "manifest_url": manifest_url,
            "preview_url": f"{request.url.scheme}://{request.url.netloc}/preview?config={encrypted_config}"
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

@app.get("/manifest.json")
async def get_manifest(config: str = Query(...)):
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))
        
        return {
            "id": "ai.companion.stremio",
            "version": "1.0.0",
            "name": "AI Companion",
            "description": "Your AI-powered movie discovery companion",
            "logo": "https://via.placeholder.com/256x256/667eea/ffffff?text=🎬",
            "resources": ["catalog"],
            "types": ["movie"],
            "catalogs": [{
                "type": "movie",
                "id": "ai_companion",
                "name": "AI Movie Discovery",
                "extra": [{"name": "search", "isRequired": True}]
            }]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid config")

@app.get("/catalog/movie/{catalog_id}.json")
async def get_catalog(catalog_id: str, config: str = Query(...), search: str = Query(...)):
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))
        
        llm_service = LLMService(config_obj)
        tmdb_service = TMDBService(config_obj.tmdb_api_key)
        rpdb_service = RPDBService(config_obj.posterdb_api_key) if config_obj.use_posterdb else None
        
        movie_titles = await llm_service.generate_movie_suggestions(search, config_obj.max_results)
        
        tasks = []
        for title in movie_titles:
            tasks.append(tmdb_service.search_movie(title))
        
        tmdb_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        metas = []
        for i, result in enumerate(tmdb_results):
            if isinstance(result, dict) and result:
                movie_details = await tmdb_service.get_movie_details(result["id"])
                if movie_details:
                    poster_url = None
                    if rpdb_service:
                        # Get IMDB ID from external_ids
                        imdb_id = movie_details.get("external_ids", {}).get("imdb_id")
                        if imdb_id:
                            poster_url = await rpdb_service.get_poster(imdb_id)
                    
                    meta = movie_to_stremio_meta(movie_details, poster_url)
                    metas.append(meta)
        
        return {"metas": metas}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)