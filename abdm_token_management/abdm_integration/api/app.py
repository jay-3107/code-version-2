# api/app.py
import asyncio
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

# Import routes directly
from .routes import token_routes, health_routes, encryption_routes
from .middlewares import setup_middlewares
from config.settings import settings
from config.logging_config import setup_logger
from utils.exceptions import TokenNotFoundError, TokenRefreshError, TokenCreationError, ABDMApiError, PublicKeyError

# Configure logging
logger = setup_logger('api')

# Create FastAPI app
def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add middlewares
    app = setup_middlewares(app)
    
    # Error handlers
    @app.exception_handler(TokenNotFoundError)
    async def token_not_found_exception_handler(request, exc):
        logger.warning(f"TokenNotFoundError: {str(exc)}")
        return JSONResponse(
            status_code=404,
            content={"detail": str(exc), "error_type": "token_not_found"}
        )

    @app.exception_handler(TokenRefreshError)
    async def token_refresh_exception_handler(request, exc):
        logger.warning(f"TokenRefreshError: {str(exc)}")
        return JSONResponse(
            status_code=401,
            content={"detail": str(exc), "error_type": "token_refresh_failed"}
        )

    @app.exception_handler(TokenCreationError)
    async def token_creation_exception_handler(request, exc):
        logger.warning(f"TokenCreationError: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "error_type": "token_creation_failed"}
        )
    
    @app.exception_handler(ABDMApiError)
    async def abdm_api_exception_handler(request, exc):
        status_code = exc.status_code if hasattr(exc, 'status_code') and exc.status_code else 500
        logger.warning(f"ABDMApiError: {str(exc)}")
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc), "error_type": "abdm_api_error"}
        )
        
    @app.exception_handler(PublicKeyError)
    async def public_key_exception_handler(request, exc):
        logger.warning(f"PublicKeyError: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc), "error_type": "public_key_error"}
        )

    # Validation error handler
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        logger.warning(f"ValidationError: {str(exc)}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc), "error_type": "validation_error"}
        )
    
    # Include routers directly - remove .router attribute
    app.include_router(token_routes)
    app.include_router(health_routes)
    app.include_router(encryption_routes)
    
    return app