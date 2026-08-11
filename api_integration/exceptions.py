"""Custom exception classes for API integration module."""

from typing import Optional


class APIIntegrationError(Exception):
    """Base exception for all API integration errors."""
    
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.details = details
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}: {self.details}"
        return self.message


class NetworkError(APIIntegrationError):
    """Raised when network connectivity issues occur."""
    pass


class APIConnectionError(APIIntegrationError):
    """Raised when API connection fails."""
    pass


class AuthenticationError(APIIntegrationError):
    """Raised when authentication fails (invalid/expired API key)."""
    pass


class InvalidAPIKeyError(AuthenticationError):
    """Raised when the API key is invalid or malformed."""
    pass


class RateLimitExceededError(APIIntegrationError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, details: Optional[str] = None):
        super().__init__(message, details)
        self.retry_after = retry_after


class PromptError(APIIntegrationError):
    """Raised when prompt building or formatting fails."""
    pass


class ConfigurationError(APIIntegrationError):
    """Raised when configuration is missing or invalid."""
    pass


class KeyringError(APIIntegrationError):
    """Raised when OS keyring operations fail."""
    pass


class EncryptionError(APIIntegrationError):
    """Raised when encryption/decryption operations fail."""
    pass