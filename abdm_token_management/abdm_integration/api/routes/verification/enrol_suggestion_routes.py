from fastapi import APIRouter, HTTPException, Query
from .models import EnrolSuggestionResponse
from .utils import call_abdm_api
from config.logging_config import setup_logger

logger = setup_logger('enrol_suggestion_routes')
router = APIRouter()

@router.get(
    "/enrol-suggestion",
    response_model=EnrolSuggestionResponse,
    summary="Get ABHA Address Suggestions",
    description="Fetch username suggestions for ABHA enrollment"
)
async def get_enrol_suggestion(
    txnId: str = Query(..., description="Transaction ID for ABHA suggestion")
):
    try:
        logger.info(f"Fetching ABHA address suggestions for txnId: {txnId}")
        abdm_url = "https://abhasbx.abdm.gov.in/abha/api/v3/enrollment/enrol/suggestion"

        # Prepare headers (add Transaction_Id)
        extra_headers = {
            "Transaction_Id": txnId
        }

        # No payload for GET; use call_abdm_api with method="GET"
        response_data = call_abdm_api(
            abdm_url,
            payload=None,
            operation_name="Enrol Suggestion",
            extra_headers=extra_headers,
            method="GET"
        )

        return {
            "txnId": response_data.get("txnId", ""),
            "abhaAddressList": response_data.get("abhaAddressList", []),
            "status": "success"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_enrol_suggestion: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error occurred: {str(e)}")