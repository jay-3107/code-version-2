# main.py - Main entry point for ABDM Integration API service

import asyncio
import uvicorn
import sys
from api.app import create_app
from services.token_manager import ABDMTokenManager
from config.settings import settings
from config.logging_config import setup_logger

# Configure logging
logger = setup_logger('main')

# Create FastAPI app
app = create_app()

# Initialize token manager 
token_manager = ABDMTokenManager()

@app.on_event("startup")
async def startup_event():
    """Start background tasks when the API server starts"""
    logger.info("Starting ABDM Integration API")
    try:
        # Start the periodic token refresh task
        asyncio.create_task(token_manager.start_periodic_refresh())
        logger.info("Periodic token refresh task started")
    except Exception as e:
        logger.critical(f"Failed to start background tasks: {str(e)}")
        # Consider raising an exception here depending on how critical these tasks are

if __name__ == "__main__":
    try:
        logger.info(f"Starting ABDM Integration API server on {settings.HOST}:{settings.PORT}")
        uvicorn.run(
            "main:app", 
            host=settings.HOST, 
            port=settings.PORT,
            reload=settings.DEBUG
        )
    except Exception as e:
        logger.critical(f"Failed to start server: {str(e)}")
        sys.exit(1)