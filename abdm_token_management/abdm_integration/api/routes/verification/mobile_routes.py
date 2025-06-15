from fastapi import APIRouter, HTTPException, Body
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from .utils import encrypt_data, call_abdm_api
from config.logging_config import setup_logger

logger = setup_logger('mobile_routes')
router = APIRouter()

# --- Models ---

class MobileOtpRequest(BaseModel):
    txnId: str = Field(..., description="Transaction ID to link this OTP request")
    mobile: str = Field(..., description="Mobile number for OTP (unencrypted)")

class MobileOtpResponse(BaseModel):
    txnId: str
    message: str
    status: str = "success"

class MobileUpdateAuthRequest(BaseModel):
    txnId: str = Field(..., description="Transaction ID for this mobile update authentication")
    otp: str = Field(..., description="OTP received on mobile (unencrypted)")

class MobileUpdateAuthResponse(BaseModel):
    txnId: str
    authResult: str
    message: str
    accounts: Optional[List[dict]] = None

# --- Endpoints ---

@router.post(
    "/initiate-mobile-otp",
    response_model=MobileOtpResponse,
    summary="Initiate Mobile Update OTP",
    description="Encrypts the mobile number and initiates OTP sending process for mobile update"
)
async def initiate_mobile_otp(request: MobileOtpRequest = Body(...)):
    """
    Initiate the mobile update OTP process.
    """
    try:
        logger.info("Initiating Mobile Update OTP request")
        if not request.mobile or len(request.mobile) != 10 or not request.mobile.isdigit():
            raise HTTPException(status_code=400, detail="Valid 10-digit mobile number is required")

        encrypted_mobile = encrypt_data(request.mobile, "Mobile Number")
        payload = {
            "txnId": request.txnId,
            "scope": ["abha-enrol", "mobile-verify"],
            "loginHint": "mobile",
            "loginId": encrypted_mobile,
            "otpSystem": "abdm"
        }
        abdm_url = "https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/request/otp"
        response_data = call_abdm_api(
            abdm_url,
            payload,
            operation_name="Mobile Update OTP"
        )
        return {
            "txnId": response_data.get("txnId", ""),
            "message": response_data.get("message", ""),
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in initiate_mobile_otp: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {str(e)}")

@router.post(
    "/auth-by-mobile-otp",
    response_model=MobileUpdateAuthResponse,
    summary="Authenticate and Link Mobile with OTP",
    description="Verifies the OTP and links the mobile number to the ABHA account"
)
async def auth_by_mobile_otp(request: MobileUpdateAuthRequest = Body(...)):
    """
    Authenticate (link) the mobile number to ABHA account using the received OTP.
    """
    try:
        logger.info("Authenticating Mobile OTP for linking mobile to ABHA")
        if not request.txnId:
            raise HTTPException(status_code=400, detail="Transaction ID is required")
        if not request.otp or not request.otp.isdigit():
            raise HTTPException(status_code=400, detail="Valid OTP is required")

        encrypted_otp = encrypt_data(request.otp, "OTP")
        payload = {
            "scope": ["abha-enrol", "mobile-verify"],
            "authData": {
                "authMethods": ["otp"],
                "otp": {
                    "timeStamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
                    "txnId": request.txnId,
                    "otpValue": encrypted_otp
                }
            }
        }
        abdm_url = "https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/auth/byAbdm"
        response_data = call_abdm_api(
            abdm_url,
            payload,
            operation_name="Mobile Update Auth By OTP"
        )
        return {
            "txnId": response_data.get("txnId", ""),
            "authResult": response_data.get("authResult", ""),
            "message": response_data.get("message", ""),
            "accounts": response_data.get("accounts", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in auth_by_mobile_otp: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {str(e)}")