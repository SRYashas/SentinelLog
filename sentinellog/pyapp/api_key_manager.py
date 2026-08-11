"""
SentinelLog — Secure API Key Manager
=====================================
Handles secure storage and retrieval of the Groq API key using:
- Primary: system keyring (Windows Credential Manager via keyring library)
- Fallback: encrypted local JSON file using cryptography.fernet

Never stores keys in plaintext.
"""

import json
import os
import base64
from pathlib import Path
from typing import Optional, Tuple

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False


SERVICE_NAME = "SentinelLog"
KEY_NAME = "groq_api_key"
CONFIG_DIR = Path(os.path.expanduser("~/.sentinellog"))
CONFIG_FILE = CONFIG_DIR / "config.enc"
SALT_FILE = CONFIG_DIR / "salt.bin"


class APIKeyManager:
    """
    Manages secure storage and retrieval of the Groq API key.
    Prefers system keyring; falls back to encrypted file storage.
    """

    def __init__(self):
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Create config directory if it doesn't exist."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    # ─── Public API ────────────────────────────────────────────────────

    def has_key(self) -> bool:
        """Check if a key is stored (either in keyring or encrypted file)."""
        return self._get_from_keyring() is not None or self._get_from_file() is not None

    def get_key(self) -> Optional[str]:
        """
        Retrieve the stored API key.
        Returns None if no key is found.
        """
        # Try keyring first
        key = self._get_from_keyring()
        if key:
            return key

        # Fall back to encrypted file
        return self._get_from_file()

    def save_key(self, api_key: str) -> bool:
        """
        Save the API key securely.
        Tries keyring first, falls back to encrypted file.
        Returns True on success.
        """
        # Validate key format (Groq keys start with gsk_)
        if not api_key.strip().startswith("gsk_"):
            return False

        # Try keyring first
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(SERVICE_NAME, KEY_NAME, api_key.strip())
                return True
            except Exception:
                pass  # Fall through to file storage

        # Fall back to encrypted file
        return self._save_to_file(api_key.strip())

    def delete_key(self) -> bool:
        """Delete the stored API key from all storage locations."""
        success = True

        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(SERVICE_NAME, KEY_NAME)
            except Exception:
                success = False

        if CONFIG_FILE.exists():
            try:
                CONFIG_FILE.unlink()
            except Exception:
                success = False

        if SALT_FILE.exists():
            try:
                SALT_FILE.unlink()
            except Exception:
                success = False

        return success

    def test_key(self, api_key: str) -> Tuple[bool, str]:
        """
        Test if an API key is valid by making a minimal request to Groq.
        Returns (success, message).
        """
        # This will be called from the UI thread, so we do a sync check
        # The actual validation happens in groq_client.validate_api_key()
        # This is a placeholder for the synchronous check
        if not api_key.strip().startswith("gsk_"):
            return False, "Invalid key format: Groq keys must start with 'gsk_'"
        return True, "Key format valid"

    # ─── Keyring Storage ──────────────────────────────────────────────

    def _get_from_keyring(self) -> Optional[str]:
        if not KEYRING_AVAILABLE:
            return None
        try:
            return keyring.get_password(SERVICE_NAME, KEY_NAME)
        except Exception:
            return None

    # ─── Encrypted File Storage (Fallback) ────────────────────────────

    def _derive_key(self, password: bytes, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password))

    def _get_or_create_salt(self) -> bytes:
        """Get existing salt or create new one."""
        if SALT_FILE.exists():
            return SALT_FILE.read_bytes()
        salt = os.urandom(16)
        SALT_FILE.write_bytes(salt)
        return salt

    def _get_machine_password(self) -> bytes:
        """
        Generate a machine-specific password for encryption.
        Uses a combination of machine ID and user info.
        """
        import platform
        import getpass

        machine_id = platform.node() + getpass.getuser()
        # Add some entropy from system
        try:
            import uuid
            machine_id += str(uuid.getnode())
        except Exception:
            pass
        return machine_id.encode()

    def _get_fernet(self) -> Fernet:
        """Get or create Fernet cipher instance."""
        salt = self._get_or_create_salt()
        password = self._get_machine_password()
        key = self._derive_key(password, salt)
        return Fernet(key)

    def _save_to_file(self, api_key: str) -> bool:
        """Save API key to encrypted file."""
        if not CRYPTOGRAPHY_AVAILABLE:
            return False

        try:
            fernet = self._get_fernet()
            data = json.dumps({"key": api_key}).encode()
            encrypted = fernet.encrypt(data)
            CONFIG_FILE.write_bytes(encrypted)
            return True
        except Exception:
            return False

    def _get_from_file(self) -> Optional[str]:
        """Retrieve API key from encrypted file."""
        if not CRYPTOGRAPHY_AVAILABLE or not CONFIG_FILE.exists():
            return None

        try:
            fernet = self._get_fernet()
            encrypted = CONFIG_FILE.read_bytes()
            decrypted = fernet.decrypt(encrypted)
            data = json.loads(decrypted.decode())
            return data.get("key")
        except Exception:
            # If decryption fails (e.g., corrupted file or different machine),
            # return None to force re-entry
            return None


# Singleton instance
_key_manager: Optional[APIKeyManager] = None


def get_key_manager() -> APIKeyManager:
    """Get the global APIKeyManager instance."""
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager