"""Authentication and API key management with secure storage."""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

import keyring
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    EncryptionError,
    InvalidAPIKeyError,
    KeyringError,
)

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "windows-event-log-analyzer"
KEYRING_USERNAME = "groq-api-key"
FALLBACK_FILE = Path.home() / ".config" / "windows-event-log-analyzer" / "credentials.enc"
SALT_FILE = Path.home() / ".config" / "windows-event-log-analyzer" / "salt.bin"


class AuthManager:
    """
    Manages secure storage and retrieval of API keys.
    
    Uses OS keyring as primary storage, with encrypted file fallback.
    """
    
    def __init__(self, app_name: str = "windows-event-log-analyzer"):
        self._app_name = app_name
        self._service_name = KEYRING_SERVICE
        self._username = KEYRING_USERNAME
        self._fallback_path = FALLBACK_FILE
        self._salt_path = SALT_FILE
        self._fernet: Optional[Fernet] = None
        self._init_fallback_storage()
    
    def _init_fallback_storage(self) -> None:
        """Initialize fallback encrypted storage directory and encryption key."""
        try:
            self._fallback_path.parent.mkdir(parents=True, exist_ok=True)
            
            if not self._salt_path.exists():
                salt = os.urandom(16)
                self._salt_path.write_bytes(salt)
                # Restrict permissions on salt file
                if hasattr(os, 'chmod'):
                    os.chmod(self._salt_path, 0o600)
            else:
                salt = self._salt_path.read_bytes()
            
            # Derive key from salt (in production, use a user password or hardware key)
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(b"app-master-key"))
            self._fernet = Fernet(key)
            
        except Exception as e:
            logger.error(f"Failed to initialize fallback storage: {e}")
            raise EncryptionError("Failed to initialize secure storage", str(e))
    
    def _encrypt(self, data: str) -> bytes:
        """Encrypt data using Fernet symmetric encryption."""
        if self._fernet is None:
            raise EncryptionError("Encryption not initialized")
        return self._fernet.encrypt(data.encode())
    
    def _decrypt(self, data: bytes) -> str:
        """Decrypt data using Fernet symmetric encryption."""
        if self._fernet is None:
            raise EncryptionError("Encryption not initialized")
        try:
            return self._fernet.decrypt(data).decode()
        except InvalidToken:
            raise EncryptionError("Decryption failed: invalid token or corrupted data")
    
    def save_api_key(self, api_key: str) -> bool:
        """
        Save API key to secure storage.
        
        Tries OS keyring first, falls back to encrypted file.
        
        Args:
            api_key: The API key to store.
            
        Returns:
            True if saved successfully.
            
        Raises:
            InvalidAPIKeyError: If the API key format is invalid.
        """
        if not api_key or not api_key.strip():
            raise InvalidAPIKeyError("API key cannot be empty")
        
        api_key = api_key.strip()
        
        # Validate basic format (Groq keys typically start with gsk_)
        if not api_key.startswith("gsk_"):
            logger.warning("API key does not match expected format (gsk_*)")
        
        # Try OS keyring first
        try:
            keyring.set_password(self._service_name, self._username, api_key)
            logger.info("API key saved to OS keyring")
            return True
        except Exception as e:
            logger.warning(f"Keyring save failed, using fallback: {e}")
        
        # Fallback to encrypted file
        try:
            encrypted = self._encrypt(api_key)
            self._fallback_path.write_bytes(encrypted)
            if hasattr(os, 'chmod'):
                os.chmod(self._fallback_path, 0o600)
            logger.info("API key saved to encrypted fallback file")
            return True
        except Exception as e:
            logger.error(f"Fallback save failed: {e}")
            raise EncryptionError("Failed to save API key to fallback storage", str(e))
    
    def get_api_key(self) -> Optional[str]:
        """
        Retrieve API key from secure storage.
        
        Returns:
            The API key if found, None otherwise.
        """
        # Try OS keyring first
        try:
            key = keyring.get_password(self._service_name, self._username)
            if key:
                logger.info("API key retrieved from OS keyring")
                return key
        except Exception as e:
            logger.warning(f"Keyring retrieval failed: {e}")
        
        # Try fallback file
        try:
            if self._fallback_path.exists():
                encrypted = self._fallback_path.read_bytes()
                key = self._decrypt(encrypted)
                logger.info("API key retrieved from encrypted fallback file")
                return key
        except Exception as e:
            logger.error(f"Fallback retrieval failed: {e}")
        
        logger.info("No API key found in any storage")
        return None
    
    def delete_api_key(self) -> bool:
        """
        Delete API key from all storage locations.
        
        Returns:
            True if deleted from at least one location.
        """
        deleted = False
        
        # Delete from keyring
        try:
            keyring.delete_password(self._service_name, self._username)
            logger.info("API key deleted from OS keyring")
            deleted = True
        except keyring.errors.PasswordDeleteError:
            pass  # Key didn't exist
        except Exception as e:
            logger.warning(f"Keyring delete failed: {e}")
        
        # Delete fallback file
        try:
            if self._fallback_path.exists():
                self._fallback_path.unlink()
                logger.info("API key deleted from fallback file")
                deleted = True
        except Exception as e:
            logger.warning(f"Fallback delete failed: {e}")
        
        return deleted
    
    def test_connection(self, api_key: Optional[str] = None) -> bool:
        """
        Test if the API key is valid by making a minimal API call.
        
        Args:
            api_key: Optional key to test. If None, uses stored key.
            
        Returns:
            True if key is valid and connection succeeds.
            
        Raises:
            AuthenticationError: If the key is invalid.
            NetworkError: If network issues prevent testing.
        """
        import httpx
        
        key = api_key or self.get_api_key()
        if not key:
            raise AuthenticationError("No API key available for testing")
        
        try:
            response = httpx.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {key}"},
                timeout=10.0,
            )
            
            if response.status_code == 200:
                logger.info("API key validation successful")
                return True
            elif response.status_code == 401:
                raise InvalidAPIKeyError("Invalid API key: authentication failed")
            elif response.status_code == 429:
                from .exceptions import RateLimitExceededError
                raise RateLimitExceededError("Rate limit exceeded during key validation")
            else:
                raise AuthenticationError(f"API validation failed: {response.status_code}")
                
        except httpx.TimeoutException:
            raise NetworkError("Connection timeout during API key validation")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error during API key validation: {e}")
    
    def has_valid_key(self) -> bool:
        """Check if a valid API key is stored."""
        key = self.get_api_key()
        if not key:
            return False
        try:
            return self.test_connection(key)
        except Exception:
            return False