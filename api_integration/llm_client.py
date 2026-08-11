"""LLM client for Groq API communication with streaming support."""

import json
import logging
from typing import AsyncGenerator, Generator, List, Optional

import httpx

from .auth_manager import AuthManager
from .exceptions import (
    APIConnectionError,
    AuthenticationError,
    InvalidAPIKeyError,
    NetworkError,
    RateLimitExceededError,
)
from .prompt_manager import PromptManager

logger = logging.getLogger(__name__)

GROQ_API_BASE = "https://api.groq.com/openai/v1"
DEFAULT_MODEL = "llama-3.1-70b-versatile"
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TEMPERATURE = 0.3


class LLMClient:
    """
    Client for communicating with Groq LLM API.
    
    Provides both synchronous and asynchronous streaming chat completions.
    Designed to run in background threads to avoid blocking the UI.
    """
    
    def __init__(
        self,
        auth_manager: AuthManager,
        prompt_manager: PromptManager,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        timeout: float = 60.0,
    ):
        self._auth_manager = auth_manager
        self._prompt_manager = prompt_manager
        self._model = model
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._async_client: Optional[httpx.AsyncClient] = None
    
    def _get_headers(self, api_key: str) -> dict:
        """Get request headers with authorization."""
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
    
    def _get_client(self) -> httpx.Client:
        """Get or create synchronous HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self._timeout)
        return self._client
    
    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create asynchronous HTTP client."""
        if self._async_client is None or self._async_client.is_closed:
            self._async_client = httpx.AsyncClient(timeout=self._timeout)
        return self._async_client
    
    def close(self) -> None:
        """Close HTTP clients."""
        if self._client and not self._client.is_closed:
            self._client.close()
        if self._async_client and not self._async_client.is_closed:
            import asyncio
            try:
                asyncio.get_event_loop().run_until_complete(self._async_client.aclose())
            except RuntimeError:
                pass  # No event loop, will be cleaned up on next use
    
    def _handle_error_response(self, response: httpx.Response) -> None:
        """Handle error responses from the API."""
        if response.status_code == 401:
            raise InvalidAPIKeyError("Invalid or expired API key")
        elif response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
            raise RateLimitExceededError(
                "Rate limit exceeded",
                retry_after=retry_seconds,
                details=response.text
            )
        elif response.status_code >= 500:
            raise APIConnectionError(f"Server error: {response.status_code}", response.text)
        elif response.status_code >= 400:
            raise APIConnectionError(f"API error: {response.status_code}", response.text)
    
    def _parse_stream_line(self, line: str) -> Optional[str]:
        """Parse a single SSE line and extract content token."""
        if not line.startswith("data: "):
            return None
        
        data = line[6:].strip()
        if data == "[DONE]":
            return None
        
        try:
            chunk = json.loads(data)
            choices = chunk.get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                content = delta.get("content")
                if content:
                    return content
        except json.JSONDecodeError:
            pass
        
        return None
    
    def stream_chat_response(
        self,
        messages: List[dict],
        api_key: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Stream chat response tokens synchronously.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            api_key: Optional API key override.
            
        Yields:
            Individual content tokens as they arrive.
            
        Raises:
            AuthenticationError: If no valid API key.
            NetworkError: If network issues occur.
            RateLimitExceededError: If rate limited.
            APIConnectionError: For other API errors.
        """
        key = api_key or self._auth_manager.get_api_key()
        if not key:
            raise AuthenticationError("No API key available")
        
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": True,
        }
        
        client = self._get_client()
        
        try:
            with client.stream(
                "POST",
                f"{GROQ_API_BASE}/chat/completions",
                headers=self._get_headers(key),
                json=payload,
            ) as response:
                self._handle_error_response(response)
                
                for line in response.iter_lines():
                    if line:
                        token = self._parse_stream_line(line)
                        if token is not None:
                            yield token
                            
        except httpx.TimeoutException:
            raise NetworkError("Request timeout during streaming")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error during streaming: {e}")
        except (AuthenticationError, RateLimitExceededError, APIConnectionError):
            raise
        except Exception as e:
            logger.error(f"Unexpected streaming error: {e}")
            raise APIConnectionError(f"Streaming failed: {e}")
    
    async def stream_chat_response_async(
        self,
        messages: List[dict],
        api_key: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response tokens asynchronously.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            api_key: Optional API key override.
            
        Yields:
            Individual content tokens as they arrive.
            
        Raises:
            AuthenticationError: If no valid API key.
            NetworkError: If network issues occur.
            RateLimitExceededError: If rate limited.
            APIConnectionError: For other API errors.
        """
        key = api_key or self._auth_manager.get_api_key()
        if not key:
            raise AuthenticationError("No API key available")
        
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": True,
        }
        
        client = self._get_async_client()
        
        try:
            async with client.stream(
                "POST",
                f"{GROQ_API_BASE}/chat/completions",
                headers=self._get_headers(key),
                json=payload,
            ) as response:
                self._handle_error_response(response)
                
                async for line in response.aiter_lines():
                    if line:
                        token = self._parse_stream_line(line)
                        if token is not None:
                            yield token
                            
        except httpx.TimeoutException:
            raise NetworkError("Request timeout during async streaming")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error during async streaming: {e}")
        except (AuthenticationError, RateLimitExceededError, APIConnectionError):
            raise
        except Exception as e:
            logger.error(f"Unexpected async streaming error: {e}")
            raise APIConnectionError(f"Async streaming failed: {e}")
    
    def chat_completion(
        self,
        messages: List[dict],
        api_key: Optional[str] = None,
    ) -> str:
        """
        Get a non-streaming chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'.
            api_key: Optional API key override.
            
        Returns:
            Complete response content.
            
        Raises:
            AuthenticationError: If no valid API key.
            NetworkError: If network issues occur.
            RateLimitExceededError: If rate limited.
            APIConnectionError: For other API errors.
        """
        key = api_key or self._auth_manager.get_api_key()
        if not key:
            raise AuthenticationError("No API key available")
        
        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "stream": False,
        }
        
        client = self._get_client()
        
        try:
            response = client.post(
                f"{GROQ_API_BASE}/chat/completions",
                headers=self._get_headers(key),
                json=payload,
            )
            self._handle_error_response(response)
            
            data = response.json()
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "")
            return ""
            
        except httpx.TimeoutException:
            raise NetworkError("Request timeout")
        except httpx.NetworkError as e:
            raise NetworkError(f"Network error: {e}")
        except (AuthenticationError, RateLimitExceededError, APIConnectionError):
            raise
        except Exception as e:
            logger.error(f"Unexpected completion error: {e}")
            raise APIConnectionError(f"Completion failed: {e}")
    
    def analyze_threat(
        self,
        log_data: dict,
        threat_score: float,
        api_key: Optional[str] = None,
    ) -> Generator[str, None, None]:
        """
        Analyze a threat using structured prompt and stream the response.
        
        This is a high-level method that builds the prompt from log data
        and streams the LLM's analysis.
        
        Args:
            log_data: Raw log data dictionary.
            threat_score: Local heuristic threat score (0-100).
            api_key: Optional API key override.
            
        Yields:
            Analysis tokens as they arrive.
        """
        messages = self._prompt_manager.build_threat_analysis_messages(log_data, threat_score)
        yield from self.stream_chat_response(messages, api_key)
    
    async def analyze_threat_async(
        self,
        log_data: dict,
        threat_score: float,
        api_key: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Async version of analyze_threat."""
        messages = self._prompt_manager.build_threat_analysis_messages(log_data, threat_score)
        async for token in self.stream_chat_response_async(messages, api_key):
            yield token