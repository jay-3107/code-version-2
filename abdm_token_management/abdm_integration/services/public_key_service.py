# services/public_key_service.py
import os
import json
import time
import base64
import requests
import schedule
import threading
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.backends import default_backend
from config.settings import settings
from config.logging_config import setup_logger
from utils.exceptions import PublicKeyError

# Configure logging
logger = setup_logger('public_key_service')

class ABDMPublicKeyManager:
    """Manages fetching, caching, and using the ABDM public key for encryption"""
    
    def __init__(self):
        """Initialize the public key manager"""
        self.logger = logger
        self.public_key = None
        self.last_fetched = None
        self.key_expires_at = None
        self.key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "abdm_public_key.pem")
        self.is_refreshing = False
        self.refresh_lock = threading.Lock()
        
    def fetch_public_key(self):
        """Fetch the latest public key from ABDM API"""
        from services.token_manager import ABDMTokenManager
        
        with self.refresh_lock:
            if self.is_refreshing:
                self.logger.info("Key refresh already in progress, skipping...")
                return
                
            self.is_refreshing = True
            
        try:
            self.logger.info("Fetching ABDM public key...")
            
            # Get access token for authorization
            token_manager = ABDMTokenManager()
            headers = token_manager.get_headers()
            
            # Make API call to get public key
            response = requests.get(
                settings.ABDM_PUBLIC_KEY_API,
                headers=headers,
                timeout=15
            )
            
            if response.status_code != 200:
                raise PublicKeyError(
                    f"Failed to fetch public key: HTTP {response.status_code}", 
                    {"status_code": response.status_code, "response": response.text}
                )
            
            # Extract the public key from response
            key_data = response.json()
            
            if not key_data.get("publicKey"):
                raise PublicKeyError(
                    "Public key not found in response", 
                    {"response": key_data}
                )
                
            # Format the public key as PEM if it's not already
            public_key = key_data["publicKey"]
            if not public_key.startswith("-----BEGIN PUBLIC KEY-----"):
                # Format as PEM
                public_key = "-----BEGIN PUBLIC KEY-----\n" + public_key + "\n-----END PUBLIC KEY-----"
            
            # Save to file
            with open(self.key_path, 'w') as f:
                f.write(public_key)
                
            # Update instance variables
            self.public_key = public_key
            self.last_fetched = datetime.now()
            
            # Set expiry to 6 months from now
            self.key_expires_at = datetime.now() + timedelta(days=180)
            
            self.logger.info("Public key fetched and saved successfully")
            return public_key
            
        except Exception as e:
            self.logger.error(f"Error fetching public key: {str(e)}")
            raise PublicKeyError(f"Failed to fetch public key: {str(e)}", {"exception": str(e)})
        finally:
            self.is_refreshing = False
            
    def get_public_key(self, force_refresh=False):
        """Get the current public key, refreshing if needed"""
        try:
            if force_refresh:
                return self.fetch_public_key()
                
            # Check if key is cached in memory
            if self.public_key and self.key_expires_at and datetime.now() < self.key_expires_at:
                return self.public_key
                
            # Check if key exists on disk
            if os.path.exists(self.key_path) and not force_refresh:
                with open(self.key_path, 'r') as f:
                    self.public_key = f.read()
                    
                # If we don't know when it expires, set it to 6 months from now
                if not self.key_expires_at:
                    self.key_expires_at = datetime.now() + timedelta(days=180)
                    
                return self.public_key
                
            # Otherwise fetch a new key
            return self.fetch_public_key()
            
        except Exception as e:
            self.logger.error(f"Error getting public key: {str(e)}")
            raise PublicKeyError(f"Failed to get public key: {str(e)}", {"exception": str(e)})
            
    def encrypt_data(self, data_str):
        """
        Encrypt data using the ABDM public key
        
        Args:
            data_str: String data to encrypt
            
        Returns:
            Base64 encoded encrypted data
        """
        try:
            # Get current public key
            pem_key = self.get_public_key()
            
            # Convert string to bytes
            data_bytes = data_str.encode('utf-8')
            
            # Load the public key
            public_key = load_pem_public_key(
                pem_key.encode('utf-8'),
                backend=default_backend()
            )
            
            # Encrypt using RSA with OAEP padding
            encrypted_data = public_key.encrypt(
                data_bytes,
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA1()),
                    algorithm=hashes.SHA1(),
                    label=None
                )
            )
            
            # Return base64 encoded result
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Error encrypting data: {str(e)}")
            raise PublicKeyError(f"Failed to encrypt data: {str(e)}", {"exception": str(e)})
            
    def start_key_refresh_scheduler(self):
        """Start scheduler to refresh the key every 6 months"""
        def refresh_job():
            self.logger.info("Scheduled public key refresh triggered")
            try:
                self.fetch_public_key()
            except Exception as e:
                self.logger.error(f"Scheduled key refresh failed: {str(e)}")
                
        # Schedule to run every 6 months (approximately 180 days)
        schedule.every(180).days.do(refresh_job)
        
        # Also schedule a daily check that will refresh if expiring within 7 days
        def check_expiry():
            try:
                if self.key_expires_at and datetime.now() > (self.key_expires_at - timedelta(days=7)):
                    self.logger.info("Public key expiring soon, refreshing...")
                    self.fetch_public_key()
            except Exception as e:
                self.logger.error(f"Key expiry check failed: {str(e)}")
                
        schedule.every().day.do(check_expiry)
        
        # Start the scheduler in a background thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(3600)  # Check every hour
                
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        self.logger.info("Public key refresh scheduler started")