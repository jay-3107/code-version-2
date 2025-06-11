# token_routes.py - Endpoints for token management

from fastapi import APIRouter, HTTPException, Depends
from services.token_manager import ABDMTokenManager
from utils.exceptions import TokenNotFoundError, TokenRefreshError, TokenCreationError
from config.logging_config import setup_logger

# Configure logging
logger = setup_logger('token_routes')

# Create router
router = APIRouter(
    prefix="",
    tags=["Token Management"],
)

# Initialize token manager
token_manager = ABDMTokenManager()

@router.post("/token", 
          summary="Create new token",
          description="Creates a new ABDM API access token using client credentials")
async def create_token(client_id: str, client_secret: str):
    """
    Create a new token, replacing any existing token
    
    Parameters:
    - **client_id**: Your ABDM client ID (e.g., SBXID_009850)
    - **client_secret**: Your ABDM client secret
    
    Returns the access token and related information
    """
    try:
        result = token_manager.create_token(client_id, client_secret)
        return result
    except TokenCreationError as e:
        logger.error(f"Failed to create token: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in create_token endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create token: {str(e)}")

@router.get("/token", 
         summary="Get current token",
         description="Get the current token from storage, refreshing if needed")
async def get_token():
    """
    Get the current token from storage
    
    Returns the access token and token type.
    If the token is expired or about to expire, it will be refreshed automatically.
    """
    try:
        return token_manager.get_token()
    except TokenNotFoundError as e:
        logger.warning(f"Token not found: {str(e)}")
        raise HTTPException(
            status_code=404, 
            detail="No token found or unable to refresh. Please create a new token."
        )
    except TokenRefreshError as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=401, 
            detail="Failed to refresh token. Please create a new token."
        )
    except Exception as e:
        logger.error(f"Error in get_token endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get token: {str(e)}")

@router.get("/token/info", 
         summary="Get token information",
         description="Get detailed information about the stored token")
async def get_token_info():
    """
    Get detailed information about the stored token
    
    Returns all token details including creation time and metadata
    """
    try:
        return token_manager.get_token_info()
    except TokenNotFoundError:
        raise HTTPException(status_code=404, detail="No valid token found. Please create a new token.")
    except Exception as e:
        logger.error(f"Error in get_token_info endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get token info: {str(e)}")

@router.get("/headers", 
         summary="Get API headers",
         description="Get complete authorization headers for ABDM API calls with a valid token")
async def get_headers():
    """
    Get the authorization headers for API calls
    
    Returns a complete set of headers you can use for ABDM API calls.
    If the token is expired or about to expire, it will be refreshed automatically.
    """
    try:
        return token_manager.get_headers()
    except TokenNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="No valid token available. Please create a new token."
        )
    except Exception as e:
        logger.error(f"Error in get_headers endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get headers: {str(e)}")