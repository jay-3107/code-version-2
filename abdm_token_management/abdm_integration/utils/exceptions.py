# exceptions.py - Custom exceptions for the ABDM integration

class ABDMBaseException(Exception):
    """Base exception for ABDM-related errors"""
    def __init__(self, message, details=None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self):
        if self.details:
            return f"{self.message} - Details: {self.details}"
        return self.message

class TokenError(ABDMBaseException):
    """Exception raised for token-related errors"""
    pass

class TokenNotFoundError(TokenError):
    """Exception raised when a token doesn't exist"""
    def __init__(self, message="No token found", details=None):
        super().__init__(message, details)

class TokenRefreshError(TokenError):
    """Exception raised when token refresh fails"""
    def __init__(self, message="Failed to refresh token", details=None):
        super().__init__(message, details)

class TokenCreationError(TokenError):
    """Exception raised when token creation fails"""
    def __init__(self, message="Failed to create token", details=None):
        super().__init__(message, details)

class ABDMApiError(ABDMBaseException):
    """Exception raised for ABDM API errors"""
    def __init__(self, message="ABDM API error", details=None, status_code=None):
        self.status_code = status_code
        super().__init__(message, details)

class EncryptionError(ABDMBaseException):
    """Exception raised for encryption-related errors"""
    def __init__(self, message="Encryption failed", details=None):
        super().__init__(message, details)