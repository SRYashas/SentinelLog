"""
Network Connectivity Monitor and Mode Switcher
Implements background thread that periodically checks for internet connectivity.
Emits signals when connectivity state changes (Offline <-> Online).
"""
import time
import socket
import requests
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal, QObject


class ConnectivityChecker(QThread):
    """
    Background thread that periodically checks for internet connectivity.
    Uses multiple methods to ensure reliable detection.
    """
    
    # Signals
    connectivity_changed = pyqtSignal(bool)  # True = Online, False = Offline
    check_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, check_interval: int = 30, timeout: int = 5):
        """
        Initialize the connectivity checker.
        
        Args:
            check_interval: Seconds between connectivity checks
            timeout: Timeout for each check attempt in seconds
        """
        super().__init__()
        self.check_interval = check_interval
        self.timeout = timeout
        self._running = False
        self._current_state = False  # Track current state to avoid duplicate signals
        
    def run(self):
        """Main thread loop - periodically checks connectivity."""
        self._running = True
        while self._running:
            is_online, message = self._check_connectivity()
            
            # Emit check completed signal
            self.check_completed.emit(is_online, message)
            
            # Only emit connectivity_changed if state actually changed
            if is_online != self._current_state:
                self._current_state = is_online
                self.connectivity_changed.emit(is_online)
            
            # Sleep for check_interval seconds, but check _running flag periodically
            for _ in range(self.check_interval):
                if not self._running:
                    break
                time.sleep(1)
    
    def stop(self):
        """Stop the monitoring thread."""
        self._running = False
        self.wait(3000)  # Wait up to 3 seconds for thread to finish
    
    def _check_connectivity(self) -> tuple[bool, str]:
        """
        Check internet connectivity using multiple methods.
        Returns (is_online, message).
        """
        # Method 1: Try to connect to a reliable DNS server (Google DNS)
        if self._check_dns():
            return True, "Online (DNS check passed)"
        
        # Method 2: Try HTTP request to a reliable endpoint
        if self._check_http():
            return True, "Online (HTTP check passed)"
        
        # Method 3: Try socket connection to a known host
        if self._check_socket():
            return True, "Online (Socket check passed)"
        
        return False, "Offline - No internet connectivity detected"
    
    def _check_dns(self) -> bool:
        """Check connectivity via DNS resolution."""
        try:
            socket.setdefaulttimeout(self.timeout)
            socket.gethostbyname("www.google.com")
class ModeManager(QObject):
    """
    Manages the application mode (Offline/Online) and coordinates UI updates.
    """
    
    # Signals
    mode_changed = pyqtSignal(str)  # "offline" or "online"
    api_key_required = pyqtSignal()  # Emitted when online mode needs API key
    
    def __init__(self, check_interval: int = 30):
        super().__init__()
        self._mode = "offline"
        self._connectivity_checker = ConnectivityChecker(check_interval=check_interval)
        self._connectivity_checker.connectivity_changed.connect(self._on_connectivity_changed)
        self._connectivity_checker.check_completed.connect(self._on_check_completed)
        self._api_key_validated = False
        
    def start_monitoring(self):
        """Start the connectivity monitoring."""
        self._connectivity_checker.start()
        # Do an initial check
        is_online, msg = self._connectivity_checker.force_check()
        self._on_connectivity_changed(is_online)
    
    def stop_monitoring(self):
        """Stop the connectivity monitoring."""
        self._connectivity_checker.stop()
    
    def _on_connectivity_changed(self, is_online: bool):
        """Handle connectivity state change."""
        new_mode = "online" if is_online else "offline"
        
        if new_mode != self._mode:
            self._mode = new_mode
            self.mode_changed.emit(new_mode)
            
            # If switching to online and no valid API key, request it
            if new_mode == "online" and not self._api_key_validated:
                self.api_key_required.emit()
    
    def _on_check_completed(self, is_online: bool, message: str):
        """Handle check completion (for UI status updates)."""
        pass  # Can be connected to status label
    
    def set_api_key_validated(self, validated: bool):
        """Mark API key as validated."""
        self._api_key_validated = validated
    
    @property
    def current_mode(self) -> str:
        """Get current mode."""
        return self._mode
    
    @property
    def is_online(self) -> bool:
        """Check if currently in online mode."""
        return self._mode == "online"
    
    def force_check(self):
        """Force an immediate connectivity check."""
        is_online, msg = self._connectivity_checker.force_check()
        self._on_connectivity_changed(is_online)
            return True
        except (socket.gaierror, socket.timeout, OSError):
            return False
    
    def _check_http(self) -> bool:
        """Check connectivity via HTTP request."""
        try:
            response = requests.get(
                "http://www.google.com/generate_204",
                timeout=self.timeout,
                allow_redirects=False
            )
            return response.status_code == 204
        except (requests.RequestException, OSError):
            return False
    
    def _check_socket(self) -> bool:
        """Check connectivity via raw socket connection."""
        try:
            sock = socket.create_connection(("8.8.8.8", 53), timeout=self.timeout)
            sock.close()
            return True
        except (OSError, socket.timeout):
            return False
    
    def force_check(self) -> tuple[bool, str]:
        """Force an immediate connectivity check (blocking)."""
        return self._check_connectivity()