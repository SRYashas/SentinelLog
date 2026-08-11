"""Network connectivity management for API integration."""

import asyncio
import logging
import socket
import threading
import time
from typing import Callable, Optional
from enum import Enum

from .exceptions import NetworkError

logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    """Represents the current network connection state."""
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class NetworkManager:
    """
    Manages network connectivity monitoring and status reporting.
    
    Provides both synchronous and asynchronous connectivity checks,
    plus a background monitoring thread that emits callbacks on state changes.
    """
    
    DEFAULT_HOST = "1.1.1.1"
    DEFAULT_PORT = 53
    DEFAULT_TIMEOUT = 3.0
    DEFAULT_CHECK_INTERVAL = 30.0
    
    def __init__(
        self,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        check_interval: float = DEFAULT_CHECK_INTERVAL,
    ):
        self._host = host
        self._port = port
        self._timeout = timeout
        self._check_interval = check_interval
        
        self._state = ConnectionState.UNKNOWN
        self._monitor_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._callbacks: list[Callable[[ConnectionState], None]] = []
        self._lock = threading.RLock()
    
    def check_connectivity(self) -> bool:
        """
        Synchronously check network connectivity by attempting TCP connection.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            with socket.create_connection((self._host, self._port), timeout=self._timeout):
                return True
        except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError) as e:
            logger.debug(f"Connectivity check failed: {e}")
            return False
    
    async def check_connectivity_async(self) -> bool:
        """
        Asynchronously check network connectivity.
        
        Returns:
            True if connection successful, False otherwise.
        """
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port),
                timeout=self._timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
            logger.debug(f"Async connectivity check failed: {e}")
            return False
    
    def get_state(self) -> ConnectionState:
        """Get the current connection state."""
        with self._lock:
            return self._state
    
    def is_online(self) -> bool:
        """Check if currently online."""
        return self.get_state() == ConnectionState.ONLINE
    
    def register_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        """
        Register a callback to be called when connection state changes.
        
        Args:
            callback: Function that accepts a ConnectionState parameter.
        """
        with self._lock:
            self._callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[ConnectionState], None]) -> None:
        """Unregister a previously registered callback."""
        with self._lock:
            if callback in self._callbacks:
                self._callbacks.remove(callback)
    
    def _notify_callbacks(self, new_state: ConnectionState) -> None:
        """Notify all registered callbacks of state change."""
        with self._lock:
            for callback in self._callbacks:
                try:
                    callback(new_state)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
    
    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while not self._stop_event.is_set():
            is_connected = self.check_connectivity()
            new_state = ConnectionState.ONLINE if is_connected else ConnectionState.OFFLINE
            
            with self._lock:
                if new_state != self._state:
                    logger.info(f"Connection state changed: {self._state.value} -> {new_state.value}")
                    self._state = new_state
                    self._notify_callbacks(new_state)
            
            self._stop_event.wait(self._check_interval)
    
    def start_monitoring(self) -> None:
        """Start background connectivity monitoring."""
        with self._lock:
            if self._monitor_thread is not None and self._monitor_thread.is_alive():
                logger.warning("Monitoring already running")
                return
            
            self._stop_event.clear()
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            logger.info("Network monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop background connectivity monitoring."""
        with self._lock:
            if self._monitor_thread is None or not self._monitor_thread.is_alive():
                return
            
            self._stop_event.set()
            self._monitor_thread.join(timeout=5.0)
            self._monitor_thread = None
            logger.info("Network monitoring stopped")
    
    def __enter__(self) -> "NetworkManager":
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop_monitoring()