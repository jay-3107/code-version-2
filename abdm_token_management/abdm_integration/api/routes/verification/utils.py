import uuid
from datetime import datetime
from fastapi import HTTPException
import requests
from typing import Dict, Any, Optional

from config.logging_config import setup_logger
from config.settings import settings
from services.token_manager import ABDMTokenManager
from services.public_key_service import ABDMPublicKeyManager
from utils.exceptions import PublicKeyError

# Configure logging and initialize managers
logger = setup_logger('verification_utils')
token_manager = ABDMTokenManager()
public_key_manager = ABDMPublicKeyManager()

def prepare_abdm_headers() -> Dict[str, str]:
    """Prepare headers for ABDM API calls with valid token"""
    try:
        headers = token_manager.get_headers()
        # Add/override standard headers
        headers["Content-Type"] = "application/json"
        headers["REQUEST-ID"] = str(uuid.uuid4())
        headers["TIMESTAMP"] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
        headers["Accept"] = "*/*"
        headers["Connection"] = "keep-alive"
        
        return headers
    except Exception as e:
        logger.error(f"Failed to prepare headers: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Authorization error: {str(e)}"
        )

def encrypt_data(data: str, purpose: str) -> str:
    """Encrypt data using ABDM public key with error handling"""
    try:
        encrypted = public_key_manager.encrypt_data(data)
        logger.debug(f"{purpose} encrypted successfully")
        return encrypted
    except PublicKeyError as e:
        logger.error(f"Failed to encrypt {purpose}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to encrypt {purpose}: {str(e)}"
        )

def call_abdm_api(
    endpoint: str,
    payload: Optional[Dict[str, Any]],
    operation_name: str,
    extra_headers: Optional[Dict[str, str]] = None,
    method: str = "POST"   # <-- Add this line
) -> Dict[str, Any]:
    """
    Make a call to ABDM API with error handling.
    Allows injecting extra headers (e.g., 'X-token').
    Supports both POST and GET methods.
    """
    headers = prepare_abdm_headers()
    if extra_headers:
        headers.update(extra_headers)
    logger.info(f"Sending {operation_name} request to {endpoint}")
    
    try:
        if method.upper() == "GET":
            response = requests.get(endpoint, headers=headers, timeout=30)
        else:
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        
        logger.debug(f"ABDM API response status: {response.status_code}")
        
        if response.status_code != 200:
            # Extract error details
            error_detail = "Unknown error"
            try:
                error_data = response.json()
                error_detail = error_data.get('message', str(error_data))
            except:
                error_detail = response.text[:200] if response.text else "No response details"
            
            logger.error(f"ABDM API error: {response.status_code} - {error_detail}")
            raise HTTPException(
                status_code=response.status_code if response.status_code != 500 else 502,
                detail=f"ABDM API error: {error_detail}"
            )
        
        return response.json()
        
    except requests.RequestException as e:
        logger.error(f"Request to ABDM API failed: {str(e)}")
        raise HTTPException(
            status_code=502,
            detail=f"Failed to communicate with ABDM API: {str(e)}"
        )