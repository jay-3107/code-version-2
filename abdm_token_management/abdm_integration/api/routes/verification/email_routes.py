from fastapi import APIRouter, HTTPException, Body
from .models import EmailVerificationRequest, EmailVerificationResponse
from .utils import encrypt_data, call_abdm_api
from config.logging_config import setup_logger

logger = setup_logger('email_routes')
router = APIRouter()

@router.post(
    "/request-email-verification-link",
    response_model=EmailVerificationResponse,
    summary="Request Email Verification Link",
    description="Encrypts the email and requests an email verification link from ABDM"
)
async def request_email_verification_link(
    req: EmailVerificationRequest = Body(...)
):
    try:
        logger.info("Requesting email verification link")
        if not req.email or "@" not in req.email:
            raise HTTPException(status_code=400, detail="Valid email address is required")
        if not req.x_token:
            raise HTTPException(status_code=400, detail="X-Token header is required")

        encrypted_email = encrypt_data(req.email, "Email")
        payload = {
            "scope": ["abha-profile", "email-link-verify"],
            "loginHint": "email",
            "loginId": encrypted_email,
            "otpSystem": "abdm"
        }
        abdm_url = "https://abhasbx.abdm.gov.in/abha/api/v3/profile/account/request/emailVerificationLink"

        # Ensure the X-token header includes 'Bearer ' prefix
        x_token_value = req.x_token.strip()
        if not x_token_value.lower().startswith("bearer "):
            x_token_value = f"Bearer {x_token_value}"

        # Pass x_token as an extra header
        extra_headers = {"X-token": x_token_value}
        response_data = call_abdm_api(
            abdm_url,
            payload,
            operation_name="Email Verification Link",
            extra_headers=extra_headers
        )

        return {
            "txnId": response_data.get("txnId", ""),
            "message": response_data.get("message", ""),
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in request_email_verification_link: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {str(e)}")