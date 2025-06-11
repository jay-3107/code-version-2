# health_routes.py - Health check endpoints

from fastapi import APIRouter
from services.token_manager import ABDMTokenManager
from config.logging_config import setup_logger

# Configure logging
logger = setup_logger('health_routes')

# Create router
router = APIRouter(
    prefix="",
    tags=["Health Checks"],
)

# Initialize token manager
token_manager = ABDMTokenManager()

@router.get("/health", 
         summary="Health check",
         description="Check if the token manager service is running properly")
async def health_check():
    """
    Health check endpoint
    
    Returns information about the service status
    """
    return token_manager.health_check()