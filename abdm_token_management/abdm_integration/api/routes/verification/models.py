# api/routes/verification/models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class AadhaarOtpRequest(BaseModel):
    aadhaar: str = Field(..., description="Aadhaar number to send OTP to")
    scope: Optional[List[str]] = Field(default=["abha-enrol"], description="Scope of the operation")
    otpSystem: str = Field(default="aadhaar", description="OTP system to use")

class AadhaarOtpResponse(BaseModel):
    txnId: str
    message: str
    status: str = "success"

class AbhaEnrollmentRequest(BaseModel):
    txnId: str = Field(..., description="Transaction ID from the OTP request")
    otp: str = Field(..., description="OTP received on Aadhaar registered mobile")
    mobile: str = Field(..., description="Mobile number for ABHA communication")

class AbhaEnrollmentResponse(BaseModel):
    status: str
    message: str
    abhaDetails: Optional[Dict] = None
    txnId: Optional[str] = None


class ABHAProfile(BaseModel):
    status: str
    profile: Dict

class ABHAProfileDetails(BaseModel):
    firstName: Optional[str] = None
    middleName: Optional[str] = None
    lastName: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None
    mobile: Optional[str] = None
    email: Optional[str] = None
    ABHANumber: Optional[str] = None
    phrAddress: Optional[List[str]] = None
    abhaStatus: Optional[str] = None
    
class MobileOtpRequest(BaseModel):
    txnId: str = Field(..., description="Transaction ID to link this OTP request")
    mobile: str = Field(..., description="Mobile number for OTP (unencrypted)")

class MobileOtpResponse(BaseModel):
    txnId: str
    message: str
    status: str = "success"
    

class EmailVerificationRequest(BaseModel):
    email: str = Field(..., description="User's email address to verify")
    x_token: str = Field(..., description="X-token for ABDM API header")

class EmailVerificationResponse(BaseModel):
    txnId: str
    message: str
    status: str = "success"
    

class EnrolSuggestionRequest(BaseModel):
    txnId: str = Field(..., description="Transaction ID for ABHA suggestion")

class EnrolSuggestionResponse(BaseModel):
    txnId: str
    abhaAddressList: List[str]
    status: str = "success"