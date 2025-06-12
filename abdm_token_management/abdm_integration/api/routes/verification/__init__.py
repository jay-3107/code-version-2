# api/routes/verification/__init__.py
from fastapi import APIRouter
from .aadhaar_routes import router as aadhaar_router

# Create a main verification router to combine all sub-routes
router = APIRouter(
    prefix="/verification",
    tags=["Verification"],
)

# Include all routes
router.include_router(aadhaar_router)

# Export the main router