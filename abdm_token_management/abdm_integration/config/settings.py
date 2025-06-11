# settings.py - Core configuration parameters for ABDM integration

import os
from datetime import timedelta

class Settings:
    def __init__(self):
        # File paths
        self.TOKEN_FILE_PATH = os.environ.get("ABDM_TOKEN_FILE", "abdm_token.json")
        
        # Token renewal settings
        self.TOKEN_REFRESH_BUFFER_SECONDS = 120  # Refresh 2 minutes before expiry
        self.TOKEN_REFRESH_INTERVAL = timedelta(minutes=15)  # Proactively check every 15 minutes
        
        # API endpoints
        self.ABDM_SESSION_API = "https://dev.abdm.gov.in/api/hiecm/gateway/v3/sessions"
        
        # Server settings
        self.HOST = "0.0.0.0"
        self.PORT = 8002
        self.DEBUG = os.environ.get("DEBUG", "False").lower() in ('true', '1', 't')
        
        # API Documentation
        self.API_TITLE = "ABDM Integration API"
        self.API_DESCRIPTION = "Services for ABDM integration including token management and data encryption"
        self.API_VERSION = "1.0.0"

# Create a global settings object
settings = Settings()