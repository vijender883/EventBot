# src/backend/utils/helper.py

import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

# You can also move allowed_file and validate_request_size here if you want
# to keep all helper functions in one place, but they are currently scoped
# within the chat.py blueprint for direct access to current_app.config.
# If moved here, they would need to import current_app.

# FastAPI specific exception handlers - add more if you want to. Basic template

async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Custom handler for Starlette/FastAPI HTTP exceptions to ensure consistent
    JSON error responses.
    """
    logger.warning(f"{exc.status_code} {exc.detail}: {request.method} {request.url.path}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )

async def method_not_allowed_handler(request: Request, exc: Exception):
    """Handle 405 errors (HTTP method not allowed)."""
    logger.warning(f"405 Method Not Allowed: {request.method} {request.url.path}")
    return JSONResponse(
        status_code=405,
        content={
            "detail": "Method not allowed",
            "message": "The HTTP method is not allowed for this endpoint."
        },
    )

async def payload_too_large_handler(request: Request, exc: Exception):
    """Handle 413 errors (payload too large)."""
    try:
        max_size_mb = request.app.state.config.MAX_FILE_SIZE // (1024 * 1024)
    except (AttributeError, KeyError):
        max_size_mb = "N/A"
    
    logger.warning(f"413 Payload Too Large: {request.url.path} - Max size {max_size_mb}MB")
    return JSONResponse(
        status_code=413,
        content={
            "success": False,
            "message": f"File or payload too large. Maximum size is {max_size_mb}MB",
            "detail": "Payload too large."
        },
    )

