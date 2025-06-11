# token_manager.py - Core token management functionality as a class

import os
import json
import time
import requests
import asyncio
from datetime import datetime

from config.settings import settings
from config.logging_config import setup_logger
from utils.exceptions import TokenNotFoundError, TokenRefreshError, TokenCreationError, ABDMApiError

class ABDMTokenManager:
    """Class to manage ABDM authentication tokens with automatic renewal"""
    
    def __init__(self):
        """Initialize the token manager"""
        self.logger = setup_logger('token_manager')
        self.refresh_task = None
        self.logger.info("ABDMTokenManager initialized")
    
    def is_token_expired_or_expiring_soon(self, token_data):
        """Check if token is expired or about to expire"""
        try:
            # Get current time in seconds since epoch
            current_time = int(time.time())
            
            # Calculate when token expires
            created_at = token_data.get("fetch_time", current_time)
            expires_in = token_data.get("expiresIn", 1200)  # Default 20 min if not specified
            expiry_time = created_at + expires_in
            
            # Check if token is expired or about to expire within buffer time
            if current_time + settings.TOKEN_REFRESH_BUFFER_SECONDS >= expiry_time:
                time_left = max(0, expiry_time - current_time)
                self.logger.info(f"Token expired or expiring soon. Time left: {time_left} seconds")
                return True
                
            self.logger.info(f"Token valid for {expiry_time - current_time} seconds")
            return False
            
        except Exception as e:
            self.logger.error(f"Error checking token expiration: {str(e)}")
            # If we can't determine expiry, assume it's expired to be safe
            return True

    def refresh_token(self, refresh_token, client_id):
        """Refresh an access token using refresh token with proper headers"""
        try:
            import uuid
            from datetime import datetime
            
            self.logger.info(f"Refreshing token for {client_id}")
            
            # Set up headers exactly as shown in Postman
            headers = {
                'Content-Type': 'application/json',
                'REQUEST-ID': str(uuid.uuid4()),  # Generate a new UUID for each request
                'TIMESTAMP': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'X-CM-ID': 'sbx',
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }
            
            payload = {
                'clientId': client_id,
                'refreshToken': refresh_token,
                'grantType': 'refresh_token'
            }
            
            response = requests.post(
                settings.ABDM_SESSION_API,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                token_data = response.json()
                token_data["fetch_time"] = int(time.time())  # Add fetch time
                self.logger.info(f"Token refreshed successfully for {client_id}")
                return token_data
            else:
                error_msg = f"Failed to refresh token: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise TokenRefreshError(error_msg, {"status_code": response.status_code})
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error while refreshing token: {str(e)}"
            self.logger.error(error_msg)
            raise TokenRefreshError(error_msg, {"exception": str(e)})
        except Exception as e:
            error_msg = f"Unexpected error refreshing token: {str(e)}"
            self.logger.error(error_msg)
            raise TokenRefreshError(error_msg, {"exception": str(e)})

    def fetch_new_token(self, client_id, client_secret):
        """Fetch a completely new token with proper headers matching ABDM API requirements"""
        try:
            import uuid
            from datetime import datetime
            
            self.logger.info(f"Fetching new token for {client_id}")
            
            # Set up headers exactly as shown in Postman
            headers = {
                'Content-Type': 'application/json',
                'REQUEST-ID': str(uuid.uuid4()),  # Generate a new UUID for each request
                'TIMESTAMP': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'X-CM-ID': 'sbx',
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }
            
            # Request payload
            payload = {
                'clientId': client_id,
                'clientSecret': client_secret,
                'grantType': 'client_credentials'
            }
            
            self.logger.debug(f"Sending token request with headers: {headers}")
            
            response = requests.post(
                settings.ABDM_SESSION_API,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code == 200:
                token_data = response.json()
                # Add fetch time to help calculate expiry
                token_data["fetch_time"] = int(time.time())
                self.logger.info(f"New token fetched successfully for {client_id}")
                return token_data
            else:
                error_msg = f"Failed to fetch token: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise TokenCreationError(error_msg, {"status_code": response.status_code})
                
        except requests.exceptions.RequestException as e:
            error_msg = f"Network error while fetching token: {str(e)}"
            self.logger.error(error_msg)
            raise TokenCreationError(error_msg, {"exception": str(e)})
        except Exception as e:
            error_msg = f"Unexpected error fetching token: {str(e)}"
            self.logger.error(error_msg)
            raise TokenCreationError(error_msg, {"exception": str(e)})

    def get_valid_token(self):
        """Get a valid token, refreshing if needed"""
        try:
            if not os.path.exists(settings.TOKEN_FILE_PATH):
                error_msg = f"Token file not found: {settings.TOKEN_FILE_PATH}"
                self.logger.error(error_msg)
                raise TokenNotFoundError(error_msg)
                
            # Load current saved data
            with open(settings.TOKEN_FILE_PATH, 'r') as f:
                saved_data = json.load(f)
                
            token_data = saved_data["token_data"]
            client_id = saved_data["client_id"]
            
            # Check if token is about to expire
            if self.is_token_expired_or_expiring_soon(token_data):
                self.logger.info("Token needs refresh")
                
                # Try to use refresh token if available
                if "refreshToken" in token_data and token_data["refreshToken"]:
                    self.logger.info("Attempting to use refresh token")
                    try:
                        new_token_data = self.refresh_token(token_data["refreshToken"], client_id)
                        
                        # If refresh succeeded, update saved data
                        if new_token_data:
                            saved_data["token_data"] = new_token_data
                            saved_data["refreshed_at"] = datetime.now().isoformat()
                            
                            with open(settings.TOKEN_FILE_PATH, 'w') as f:
                                json.dump(saved_data, f, indent=2)
                                
                            self.logger.info("Token refreshed and saved")
                            return saved_data
                    except TokenRefreshError:
                        self.logger.warning("Refresh token failed, trying client credentials")
                    
                # If we don't have a refresh token or refresh failed,
                # we need client_secret to get a completely new token
                if "client_secret" in saved_data:
                    self.logger.info("Getting completely new token")
                    client_secret = saved_data["client_secret"]
                    
                    new_token_data = self.fetch_new_token(client_id, client_secret)
                    if new_token_data:
                        # Update saved data with new token
                        saved_data["token_data"] = new_token_data
                        saved_data["refreshed_at"] = datetime.now().isoformat()
                        
                        # Save updated data
                        with open(settings.TOKEN_FILE_PATH, 'w') as f:
                            json.dump(saved_data, f, indent=2)
                            
                        self.logger.info("New token fetched and saved")
                        return saved_data
                else:
                    error_msg = "Token expired and client_secret not available for renewal"
                    self.logger.error(error_msg)
                    raise TokenRefreshError(error_msg)
            
            # Token is still valid
            return saved_data
            
        except (TokenNotFoundError, TokenRefreshError) as e:
            # Re-raise expected exceptions
            raise
        except Exception as e:
            error_msg = f"Unexpected error in get_valid_token: {str(e)}"
            self.logger.error(error_msg)
            raise TokenRefreshError(error_msg, {"exception": str(e)})

    def create_token(self, client_id, client_secret):
        """Create a new token, replacing any existing token"""
        try:
            self.logger.info(f"Creating new token for {client_id}")
            
            # Use our helper function to fetch the token
            token_data = self.fetch_new_token(client_id, client_secret)
            
            # Save to file with additional metadata
            save_data = {
                "token_data": token_data,
                "created_at": datetime.now().isoformat(),
                "client_id": client_id,
                "client_secret": client_secret  # Store for automatic renewal
            }
            
            with open(settings.TOKEN_FILE_PATH, 'w') as f:
                json.dump(save_data, f, indent=2)
                
            self.logger.info(f"Token saved to {settings.TOKEN_FILE_PATH}")
            
            # Return in the same format as ABDM API
            return {
                "accessToken": token_data["accessToken"],
                "tokenType": token_data["tokenType"],
                "expiresIn": token_data["expiresIn"],
                "refreshExpiresIn": token_data.get("refreshExpiresIn", 1800),
                "refreshToken": token_data.get("refreshToken", "")
            }
                
        except (TokenCreationError) as e:
            # Re-raise expected exceptions
            raise
        except Exception as e:
            error_msg = f"Unexpected error creating token: {str(e)}"
            self.logger.error(error_msg)
            raise TokenCreationError(error_msg, {"exception": str(e)})
    
    def get_token(self):
        """Get the current token from storage, refreshing if needed"""
        try:
            # Get valid token (refreshing if needed)
            saved_data = self.get_valid_token()
            
            token_data = saved_data["token_data"]
            
            return {
                "access_token": token_data["accessToken"],
                "token_type": token_data["tokenType"]
            }
        except Exception as e:
            self.logger.error(f"Exception getting token: {str(e)}")
            raise

    def get_token_info(self):
        """Get detailed information about the stored token"""
        try:
            # Get valid token (refreshing if needed)
            saved_data = self.get_valid_token()
            
            # Create a copy to avoid modifying the original
            response_data = json.loads(json.dumps(saved_data))
            
            # Add expiry information
            if "token_data" in response_data and "fetch_time" in response_data["token_data"]:
                fetch_time = response_data["token_data"]["fetch_time"]
                expires_in = response_data["token_data"].get("expiresIn", 1200)
                
                expiry_time = fetch_time + expires_in
                response_data["expiry_time"] = expiry_time
                response_data["expires_at"] = datetime.fromtimestamp(expiry_time).isoformat()
                
                # Calculate remaining time
                current_time = int(time.time())
                response_data["remaining_seconds"] = max(0, expiry_time - current_time)
                
            # Remove sensitive information
            if "token_data" in response_data and "clientSecret" in response_data["token_data"]:
                response_data["token_data"]["clientSecret"] = "********"
            
            if "client_secret" in response_data:
                response_data["client_secret"] = "********"
                
            return response_data
        except Exception as e:
            self.logger.error(f"Exception getting token info: {str(e)}")
            raise

    def get_headers(self):
        """Get the authorization headers for API calls to ABDM"""
        try:
            # Get valid token (refreshing if needed)
            saved_data = self.get_valid_token()
            
            token_data = saved_data["token_data"]
            import uuid
            from datetime import datetime
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {token_data['accessToken']}",
                'REQUEST-ID': str(uuid.uuid4()),  # Generate a new UUID for each request
                'TIMESTAMP': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
                'X-CM-ID': 'sbx',
                'Accept': '*/*',
                'Connection': 'keep-alive'
            }
            
            # Add X-Token-Expiry header for information
            if "fetch_time" in token_data and "expiresIn" in token_data:
                expires_at = datetime.fromtimestamp(token_data["fetch_time"] + token_data["expiresIn"])
                headers['X-Token-Expiry'] = expires_at.isoformat()
            
            return headers
        except Exception as e:
            self.logger.error(f"Exception getting headers: {str(e)}")
            raise

    def health_check(self):
        """Health check function"""
        token_exists = os.path.exists(settings.TOKEN_FILE_PATH)
        token_status = "not_found"
        
        if token_exists:
            try:
                with open(settings.TOKEN_FILE_PATH, 'r') as f:
                    saved_data = json.load(f)
                
                if "token_data" in saved_data:
                    token_data = saved_data["token_data"]
                    if self.is_token_expired_or_expiring_soon(token_data):
                        token_status = "expiring_soon"
                    else:
                        token_status = "valid"
            except:
                token_status = "invalid_format"
        
        return {
            "status": "healthy",
            "service": "ABDM Token Manager",
            "current_time": datetime.now().isoformat(),
            "token_exists": token_exists,
            "token_status": token_status,
            "current_timestamp": int(time.time())
        }

    async def start_periodic_refresh(self):
        """Start a background task to periodically check and refresh the token"""
        self.logger.info(f"Starting periodic token refresh task (every {settings.TOKEN_REFRESH_INTERVAL})")
        
        while True:
            try:
                # Check if token exists and try to refresh it if needed
                if os.path.exists(settings.TOKEN_FILE_PATH):
                    self.logger.info("Periodic token check triggered")
                    try:
                        self.get_valid_token()
                        self.logger.info("Periodic token check completed successfully")
                    except TokenNotFoundError:
                        self.logger.warning("No token found during periodic check")
                    except Exception as e:
                        self.logger.error(f"Error during periodic token check: {str(e)}")
            except Exception as e:
                self.logger.error(f"Unexpected error in periodic refresh: {str(e)}")
            
            # Wait for the next interval
            await asyncio.sleep(settings.TOKEN_REFRESH_INTERVAL.total_seconds())