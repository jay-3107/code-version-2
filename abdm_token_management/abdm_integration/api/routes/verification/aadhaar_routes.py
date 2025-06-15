# api/routes/verification/aadhaar_routes.py
from fastapi import APIRouter, HTTPException, Body
import uuid

from config.logging_config import setup_logger
from config.settings import settings
from .models import AadhaarOtpRequest, AadhaarOtpResponse, AbhaEnrollmentRequest, AbhaEnrollmentResponse
from .utils import encrypt_data, call_abdm_api
from services.abha_profile_service import ABHAProfileManager
# Configure logging
logger = setup_logger('aadhaar_routes')
abha_profile_manager = ABHAProfileManager()

# Create router - we'll combine this into the main verification router
router = APIRouter()

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
        encrypted_aadhaar = encrypt_data(request.aadhaar, "Aadhaar")
            
        # 3. Prepare the payload
        payload = {
            "txnId": "",  # Empty as per your example
            "scope": request.scope,
            "loginHint": "aadhaar",
            "loginId": encrypted_aadhaar,
            "otpSystem": request.otpSystem
        }
        
        # 4. Call ABDM API and handle the response
        response_data = call_abdm_api(
            settings.ABDM_INITIATE_OTP_API, 
            payload, 
            "Aadhaar OTP initiation"
        )
        
        # 5. Process successful response
        logger.info(f"OTP initiation successful, txnId: {response_data.get('txnId', 'unknown')}")
        
        return {
            "txnId": response_data.get("txnId", ""),
            "message": response_data.get("message", "OTP sent successfully"),
            "status": "success"
        }
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in initiate_aadhaar_otp: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error occurred: {str(e)}"
        )

@router.post("/enroll-by-aadhaar",
         #response_model=AbhaEnrollmentResponse,
         summary="Complete ABHA enrollment with Aadhaar OTP",
         description="Completes ABHA enrollment process after OTP verification")
async def enroll_by_aadhaar(request: AbhaEnrollmentRequest = Body(...)):
    """
    Complete the ABHA enrollment process using Aadhaar OTP verification
    
    This endpoint:
    1. Encrypts the OTP using ABDM public key
    2. Sends enrollment request with transaction ID, encrypted OTP and mobile number
    3. Returns ABHA details upon successful enrollment
    
    Parameters:
    - **txnId**: Transaction ID received from initiate-aadhaar-otp call
    - **otp**: The OTP received on Aadhaar registered mobile
    - **mobile**: Mobile number for ABHA communication
    
    Returns the enrollment status and ABHA details if successful
    """
    try:
        logger.info(f"Processing ABHA enrollment request with txnId: {request.txnId}")
        
        # 1. Validate inputs
        if not request.txnId:
            raise HTTPException(
                status_code=400, 
                detail="Transaction ID is required"
            )
            
        if not request.otp or not request.otp.isdigit():
            raise HTTPException(
                status_code=400,
                detail="Valid OTP is required"
            )
            
        if not request.mobile or len(request.mobile) != 10 or not request.mobile.isdigit():
            raise HTTPException(
                status_code=400,
                detail="Valid 10-digit mobile number is required"
            )
            
        # 2. Encrypt the OTP
        encrypted_otp = encrypt_data(request.otp, "OTP")
            
        # 3. Prepare the payload
        payload = {
            "authData": {
                "authMethods": [
                    "otp"
                ],
                "otp": {
                    "txnId": request.txnId,
                    "otpValue": encrypted_otp,
                    "mobile": request.mobile
                }
            },
            "consent": {
                "code": "abha-enrollment",
                "version": "1.4"
            }
        }
        
        # 4. Call ABDM API
        response_data = call_abdm_api(
            settings.ABDM_ENROLL_API, 
            payload, 
            "ABHA enrollment"
        )

        # 5. Process successful response and save complete profile data
        logger.info(f"ABHA enrollment successful")

        # Save the complete ABHA profile data
        if "ABHAProfile" in response_data:
            abha_profile_manager.save_profile(response_data)
            logger.info(f"ABHA profile saved for {response_data.get('ABHAProfile', {}).get('ABHANumber', 'unknown')}")

        # Return the FULL response as-is
        return response_data
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in enroll_by_aadhaar: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error occurred: {str(e)}"
        )
        
@router.get("/abha-profile",
         summary="Get stored ABHA profile",
         description="Get the complete ABHA profile from storage")
async def get_abha_profile():
    """
    Get the stored ABHA profile information
    
    Returns the complete ABHA profile details previously received from ABDM
    """
    try:
        profile = abha_profile_manager.get_profile()
        
        if not profile:
            raise HTTPException(
                status_code=404,
                detail="No ABHA profile found. Please complete enrollment first."
            )
            
        return {
            "status": "success",
            "profile": profile
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving ABHA profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve ABHA profile: {str(e)}"
        )