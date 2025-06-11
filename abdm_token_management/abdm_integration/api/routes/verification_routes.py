# api/routes/verification_routes.py
from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import Optional, List
import uuid
import requests
from datetime import datetime

from config.settings import settings
from config.logging_config import setup_logger
from services.token_manager import ABDMTokenManager
from services.public_key_service import ABDMPublicKeyManager
from utils.exceptions import PublicKeyError

# Configure logging
logger = setup_logger('verification_routes')

# Create router
router = APIRouter(
    prefix="/verification",
    tags=["Verification"],
)

# Initialize managers
token_manager = ABDMTokenManager()
public_key_manager = ABDMPublicKeyManager()

class AadhaarOtpRequest(BaseModel):
    aadhaar: str = Field(..., description="Aadhaar number to send OTP to")
    scope: Optional[List[str]] = Field(default=["abha-enrol"], description="Scope of the operation")
    otpSystem: str = Field(default="aadhaar", description="OTP system to use")

class AadhaarOtpResponse(BaseModel):
    txnId: str
    message: str
    status: str = "success"

@router.post("/initiate-aadhaar-otp",
         response_model=AadhaarOtpResponse,
         summary="Initiate Aadhaar OTP process",
         description="Encrypts the Aadhaar number and initiates OTP sending process")
async def initiate_aadhaar_otp(request: AadhaarOtpRequest = Body(...)):
    """
    Initiate the Aadhaar OTP verification process
    
    This endpoint:
    1. Encrypts the Aadhaar number using ABDM public key
    2. Sends a request to ABDM API to initiate OTP sending to the registered mobile
    3. Returns the transaction ID needed for OTP verification
    
    Parameters:
    - **aadhaar**: Aadhaar number to verify
    - **scope**: List of scopes, defaults to ["abha-enrol"]
    - **otpSystem**: OTP system to use, defaults to "aadhaar"
    
    Returns the transaction ID and success message
    """
    try:
        logger.info(f"Initiating Aadhaar OTP verification")
        
        # 1. Validate Aadhaar format
        if not request.aadhaar or len(request.aadhaar) != 12 or not request.aadhaar.isdigit():
            raise HTTPException(
                status_code=400, 
                detail="Invalid Aadhaar number. Must be exactly 12 digits."
            )
            
        # 2. Encrypt Aadhaar number
        try:
            encrypted_aadhaar = public_key_manager.encrypt_data(request.aadhaar)
            logger.debug("Aadhaar encrypted successfully")
        except PublicKeyError as e:
            logger.error(f"Failed to encrypt Aadhaar: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to encrypt Aadhaar: {str(e)}"
            )
            
        # 3. Prepare headers with valid token
        try:
            headers = token_manager.get_headers()
            # Explicitly add/override certain headers as in Postman
            headers["Content-Type"] = "application/json"
            headers["REQUEST-ID"] = str(uuid.uuid4())
            headers["TIMESTAMP"] = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            headers["Accept"] = "*/*"
            headers["Connection"] = "keep-alive"
            
            logger.debug(f"Using headers: {headers.get('REQUEST-ID')}")
        except Exception as e:
            logger.error(f"Failed to get valid token/headers: {str(e)}")
            raise HTTPException(
                status_code=401,
                detail=f"Authorization error: {str(e)}"
            )
            
        # 4. Prepare the payload as specified by you
        payload = {
            "txnId": "",  # Empty as per your example
            "scope": request.scope,
            "loginHint": "aadhaar",
            "loginId": encrypted_aadhaar,
            "otpSystem": request.otpSystem
        }
        
        # Log the request (hiding sensitive data)
        logger.info(f"Sending request to {settings.ABDM_INITIATE_OTP_API}")
        logger.debug(f"Request payload: {str({**payload, 'loginId': '[ENCRYPTED]'})}")
        
        # 5. Send the request to ABDM API
        try:
            response = requests.post(
                settings.ABDM_INITIATE_OTP_API,
                headers=headers,
                json=payload,
                timeout=30  # Extended timeout for OTP operations
            )
            
            logger.debug(f"ABDM API response status: {response.status_code}")
            
            if response.status_code != 200:
                # Try to extract error details
                error_detail = "Unknown error"
                try:
                    error_data = response.json()
                    error_detail = error_data.get('message', error_data)
                except:
                    error_detail = response.text[:200] if response.text else "No response details"
                
                logger.error(f"ABDM API error: {response.status_code} - {error_detail}")
                raise HTTPException(
                    status_code=response.status_code if response.status_code != 500 else 502,
                    detail=f"ABDM API error: {error_detail}"
                )
                
            # 6. Process successful response
            response_data = response.json()
            logger.info(f"OTP initiation successful, txnId: {response_data.get('txnId', 'unknown')}")
            
            return {
                "txnId": response_data.get("txnId", ""),
                "message": response_data.get("message", "OTP sent successfully"),
                "status": "success"
            }
            
        except requests.RequestException as e:
            logger.error(f"Request to ABDM API failed: {str(e)}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to communicate with ABDM API: {str(e)}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in initiate_aadhaar_otp: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error occurred: {str(e)}"
        )