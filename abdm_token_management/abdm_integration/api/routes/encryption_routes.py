# api/routes/encryption_routes.py
from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
import json

from config.logging_config import setup_logger
from services.public_key_service import ABDMPublicKeyManager
from utils.exceptions import PublicKeyError

# Configure logging
logger = setup_logger('encryption_routes')

# Create router
router = APIRouter(
    prefix="/encryption",
    tags=["Encryption"],
)

# Initialize public key manager
public_key_manager = ABDMPublicKeyManager()

class EncryptionRequest(BaseModel):
    data: str
    description: Optional[str] = None

class EncryptionResponse(BaseModel):
    encrypted_data: str
    status: str = "success"

@router.post("/encrypt", 
         response_model=EncryptionResponse,
         summary="Encrypt data with ABDM public key",
         description="Encrypts input data using the ABDM public key with RSA/ECB/OAEPWithSHA-1AndMGF1Padding")
async def encrypt_data(
    request: EncryptionRequest = Body(...),
):
    """
    Encrypt data using the ABDM public key
    
    Parameters:
    - **data**: String data to encrypt (e.g., Aadhaar number or OTP)
    - **description**: Optional description of what is being encrypted
    
    Returns the base64 encoded encrypted data
    """
    try:
        logger.info(f"Encrypting data")
        if request.description:
            logger.info(f"Description: {request.description}")
            
        # Encrypt the data
        encrypted = public_key_manager.encrypt_data(request.data)
        
        logger.info(f"Data encrypted successfully")
        return {"encrypted_data": encrypted, "status": "success"}
        
    except PublicKeyError as e:
        logger.error(f"Public key error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Encryption failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in encrypt_data endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Encryption failed: {str(e)}")

@router.get("/public-key", 
         summary="Get current public key",
         description="Retrieves the current ABDM public key being used for encryption")
async def get_public_key(
    refresh: bool = Query(False, description="Force refresh the public key"),
):
    """
    Get the current ABDM public key
    
    Parameters:
    - **refresh**: Set to true to force refresh the key from ABDM API
    
    Returns the public key in PEM format
    """
    try:
        logger.info(f"User requesting public key")
        key = public_key_manager.get_public_key(force_refresh=refresh)
        return {"public_key": key, "status": "success"}
    except PublicKeyError as e:
        logger.error(f"Public key error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get public key: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in get_public_key endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get public key: {str(e)}")

# Unified API that handles both token and encryption
class UnifiedRequest(BaseModel):
    data: str
    description: Optional[str] = None
    client_id: Optional[str] = None
    client_secret: Optional[str] = None

@router.post("/secure-encrypt", 
         summary="One-step encrypt with token handling",
         description="Gets/refreshes token if needed and encrypts data in one step")
async def secure_encrypt(
    request: UnifiedRequest = Body(...),
):
    """
    Unified API that handles token management and encryption in one step
    
    Parameters:
    - **data**: String data to encrypt (e.g., Aadhaar number or OTP)
    - **description**: Optional description of what is being encrypted
    - **client_id**: Optional client ID to create a new token if needed
    - **client_secret**: Optional client secret to create a new token if needed
    
    Returns the base64 encoded encrypted data and token status
    """
    try:
        logger.info(f"Using secure-encrypt endpoint")
        
        # Handle token if needed
        from services.token_manager import ABDMTokenManager
        token_manager = ABDMTokenManager()
        token_status = "existing"
        
        try:
            # Try to get existing token
            token_info = token_manager.get_token_info()
        except Exception as e:
            logger.warning(f"No valid token available: {str(e)}")
            
            # Check if we have client credentials to create a new token
            if request.client_id and request.client_secret:
                logger.info("Creating new token with provided credentials")
                token_info = token_manager.create_token(request.client_id, request.client_secret)
                token_status = "created"
            else:
                logger.error("No valid token and no credentials provided")
                raise HTTPException(
                    status_code=401,
                    detail="No valid token available. Please provide client_id and client_secret or create a token first."
                )
        
        # Now encrypt the data
        encrypted = public_key_manager.encrypt_data(request.data)
        
        return {
            "encrypted_data": encrypted, 
            "token_status": token_status,
            "status": "success"
        }
        
    except PublicKeyError as e:
        logger.error(f"Public key error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Encryption failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in secure_encrypt endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")