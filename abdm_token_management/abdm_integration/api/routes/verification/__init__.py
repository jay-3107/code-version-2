from fastapi import APIRouter
from .aadhaar_routes import router as aadhaar_router
from .mobile_routes import router as mobile_router
from .email_routes import router as email_router
from .enrol_suggestion_routes import router as enrol_suggestion_router

# Create a main verification router to combine all sub-routes
router = APIRouter(
    prefix="/verification",
    tags=["Verification"],
)

# Include all routes
router.include_router(aadhaar_router)
router.include_router(mobile_router)
router.include_router(email_router)
router.include_router(enrol_suggestion_router)
# Export the main router