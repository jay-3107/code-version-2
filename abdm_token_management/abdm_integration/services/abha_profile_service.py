# services/abha_profile_service.py
import os
import json
from datetime import datetime
from config.logging_config import setup_logger
from config.settings import settings

# Configure logging
logger = setup_logger('abha_profile_service')

class ABHAProfileManager:
    """
    Manages storage and retrieval of ABHA profile information
    """
    
    def __init__(self):
        """Initialize the ABHA profile manager"""
        self.logger = logger
        self.profile_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), settings.ABHA_PROFILE_FILE_PATH)
        
    def save_profile(self, profile_data):
        """
        Save ABHA profile data to persistent storage
        
        Args:
            profile_data: The complete profile data from ABDM API
        """
        try:
            # Add timestamp for record keeping
            profile_data_with_meta = {
                "profile": profile_data,
                "savedAt": datetime.now().isoformat(),
                "updatedAt": datetime.now().isoformat()
            }
            
            # Save to file
            with open(self.profile_file, 'w') as f:
                json.dump(profile_data_with_meta, f, indent=2)
                
            self.logger.info(f"ABHA profile saved successfully for {profile_data.get('ABHAProfile', {}).get('ABHANumber', 'unknown')}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving ABHA profile: {str(e)}")
            return False
        
    def get_profile(self):
        """
        Get the stored ABHA profile
        
        Returns:
            The ABHA profile data or None if not available
        """
        try:
            if os.path.exists(self.profile_file):
                with open(self.profile_file, 'r') as f:
                    return json.load(f).get("profile", {})
            else:
                self.logger.warning("No ABHA profile file found")
                return None
        except Exception as e:
            self.logger.error(f"Error loading ABHA profile: {str(e)}")
            return None
            
    def update_profile(self, updated_data):
        """
        Update specific fields in the profile
        
        Args:
            updated_data: Dictionary containing fields to update
        """
        try:
            current_data = self.get_profile()
            
            if not current_data:
                self.logger.warning("Cannot update profile as no existing profile found")
                return False
                
            # Update only provided fields
            if "ABHAProfile" in current_data and "ABHAProfile" in updated_data:
                current_data["ABHAProfile"].update(updated_data["ABHAProfile"])
            
            # Add any new fields that don't exist
            for key, value in updated_data.items():
                if key != "ABHAProfile" and key not in current_data:
                    current_data[key] = value
            
            # Save the updated profile
            with open(self.profile_file, 'r') as f:
                full_data = json.load(f)
                
            full_data["profile"] = current_data
            full_data["updatedAt"] = datetime.now().isoformat()
            
            with open(self.profile_file, 'w') as f:
                json.dump(full_data, f, indent=2)
                
            self.logger.info("ABHA profile updated successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error updating ABHA profile: {str(e)}")
            return False