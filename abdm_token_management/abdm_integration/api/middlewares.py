# middlewares.py - API middlewares for the ABDM integration

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import time
from config.logging_config import setup_logger

logger = setup_logger('middlewares')

# CORS middleware configuration
def setup_cors(app):
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    return app

# Request logging middleware
class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log the request
        logger.info(f"Request started: {request.method} {request.url.path}")
        
        # Process the request
        response = await call_next(request)
        
        # Log the response time
        process_time = time.time() - start_time
        logger.info(f"Request completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
        
        return response

def setup_middlewares(app):
    # Setup CORS
    app = setup_cors(app)
    
    # Add request logging
    app.add_middleware(RequestLoggingMiddleware)
    
    return app