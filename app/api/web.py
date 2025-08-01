"""
Web UI routes for the Stremio AI Companion application.
"""

import json
from typing import Optional

from fastapi import APIRouter, Request, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import ValidationError
from starlette.templating import Jinja2Templates

from app.core.config import settings
from app.core.logging import logger
from app.models.config import Config
from app.services.encryption import encryption_service


def get_request_scheme(request: Request) -> str:
    """
    Determine the correct scheme (http or https) based on request headers.

    This handles cases where the application is behind a proxy (like in Docker)
    that might forward requests internally using HTTP even if the original request
    was HTTPS.

    Args:
        request: The FastAPI request object

    Returns:
        The correct scheme (http or https)
    """
    # Check X-Forwarded-Proto header (common in proxy setups)
    forwarded_proto = request.headers.get("X-Forwarded-Proto")
    if forwarded_proto:
        return forwarded_proto

    # Check Forwarded header (RFC 7239)
    forwarded = request.headers.get("Forwarded")
    if forwarded:
        for part in forwarded.split(";"):
            if part.strip().startswith("proto="):
                return part.strip()[6:]

    # Fall back to the request's scheme
    return request.url.scheme


router = APIRouter(tags=["Web UI"])
templates = Jinja2Templates(directory="templates")


@router.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    """
    Render the homepage with application description and configuration options.
    """
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/configure", response_class=HTMLResponse)
async def configure_page(request: Request, config: Optional[str] = Query(None)):
    """
    Render the configuration page.

    If a config parameter is provided, it will pre-fill the form with existing settings.
    """
    existing_config = None
    if config:
        try:
            config_data = encryption_service.decrypt(config)
            existing_config = Config.model_validate(json.loads(config_data))
        except Exception as e:
            # If config is invalid, just show empty form
            logger.warning(f"Invalid config provided to configure page: {e}")
            pass

    return templates.TemplateResponse(
        "configure.html", {"request": request, "existing_config": existing_config, "settings": settings}
    )


@router.get("/config/{config}/preview", response_class=HTMLResponse)
async def preview_page(request: Request, config: str):
    """
    Render the preview page with configuration details and manifest URL.
    """
    try:
        config_data = encryption_service.decrypt(config)
        config_obj = Config.model_validate(json.loads(config_data))
        scheme = get_request_scheme(request)

        # Build manifest URLs for all types
        base_url = f"{scheme}://{request.url.netloc}/config/{config}"
        manifest_urls = {
            "combined": f"{base_url}/manifest.json",
            "movie": f"{base_url}/movie/manifest.json",
            "series": f"{base_url}/series/manifest.json",
        }

        return templates.TemplateResponse(
            "preview.html",
            {
                "request": request,
                "manifest_url": manifest_urls["combined"],  # Keep backward compatibility
                "manifest_urls": manifest_urls,
                "config": config_obj,
            },
        )
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in preview: {e}")
        raise HTTPException(status_code=400, detail="Invalid config format")
    except ValidationError as e:
        logger.error(f"Validation error in preview: {e}")
        raise HTTPException(status_code=400, detail="Invalid config data")
    except Exception as e:
        logger.error(f"General error in preview: {e}")
        raise HTTPException(status_code=400, detail=f"Config error: {str(e)}")


@router.post("/save-config")
async def save_config(
    request: Request,
    openai_api_key: str = Form(...),
    openai_base_url: str = Form("https://openrouter.ai/api/v1"),
    model_name: str = Form("openrouter/horizon-alpha:online"),
    tmdb_read_access_token: str = Form(...),
    max_results: int = Form(20),
    include_adult: Optional[str] = Form(None),
    use_posterdb: Optional[str] = Form(None),
    posterdb_api_key: str = Form(""),
):
    """
    Save configuration settings and return manifest URL.

    Handles form submission from the configure page, validates the settings,
    and returns URLs for the manifest and preview page.
    """
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
            posterdb_api_key=posterdb_api_key if posterdb_api_key else None,
        )

        encrypted_config = encryption_service.encrypt(config.model_dump_json())
        scheme = get_request_scheme(request)

        # Build manifest URLs for all types
        base_url = f"{scheme}://{request.url.netloc}/config/{encrypted_config}"
        manifest_urls = {
            "combined": f"{base_url}/manifest.json",
            "movie": f"{base_url}/movie/manifest.json",
            "series": f"{base_url}/series/manifest.json",
        }

        return JSONResponse(
            {
                "success": True,
                "manifest_url": manifest_urls["combined"],  # Keep backward compatibility
                "manifest_urls": manifest_urls,
                "preview_url": f"{base_url}/preview",
            }
        )
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            field = error["loc"][-1] if error["loc"] else "unknown"
            message = error["msg"]
            error_messages.append(f"{field}: {message}")

        return JSONResponse(
            {"success": False, "detail": "Validation failed: " + "; ".join(error_messages)}, status_code=400
        )
    except Exception as e:
        return JSONResponse({"success": False, "detail": f"Configuration error: {str(e)}"}, status_code=500)


@router.get("/config/{config}")
async def config_redirect(config: str):
    """
    Redirect to configure page with existing config.
    """
    return RedirectResponse(url=f"/configure?config={config}")
