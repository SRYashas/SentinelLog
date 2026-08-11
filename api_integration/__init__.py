"""API Integration package for Windows Event Log Analyzer.

This package provides modular backend components for:
- Network connectivity monitoring
- Secure API key management
- LLM communication (Groq API)
- Prompt engineering and management
"""

from .auth_manager import AuthManager
from .exceptions import (
    APIConnectionError,
    APIIntegrationError,
    AuthenticationError,
    ConfigurationError,
    EncryptionError,
    InvalidAPIKeyError,
    KeyringError,
    NetworkError,
    PromptError,
    RateLimitExceededError,
)
from .llm_client import LLMClient
from .network_manager import ConnectionState, NetworkManager
from .prompt_manager import PromptManager

__all__ = [
    # Core classes
    "NetworkManager",
    "AuthManager",
    "LLMClient",
    "PromptManager",
    # Enums
    "ConnectionState",
    # Exceptions
    "APIIntegrationError",
    "NetworkError",
    "APIConnectionError",
    "AuthenticationError",
    "InvalidAPIKeyError",
    "RateLimitExceededError",
    "PromptError",
    "ConfigurationError",
    "KeyringError",
    "EncryptionError",
]

__version__ = "1.0.0"