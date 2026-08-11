"""
SentinelLog — Network Connectivity Monitor
===========================================
Background thread that periodically checks for internet connectivity
and emits signals when online/offline state changes.
"""

import socket
import time
from typing import Optional
from PyQt6.QtCore import QThread, pyqtSignal


class ConnectivityMonitor(QThread):
    """
    Monitors internet connectivity in a background thread.
    Emits `connectivity_changed(bool)` when state changes.
    """

    connectivity_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        check_interval: int = 30,
        timeout: int = 5,
        test_hosts: Optional[list] = None,
        parent=None
    ):
        super().__init__(parent)
        self.check_interval = check_interval
        self.timeout = timeout
        self.test_hosts = test_hosts or [
            ("8.8.8.8", 53),      # Google DNS
            ("1.1.1.1", 53),      # Cloudflare DNS
            ("api.groq.com", 443), # Groq API endpoint
        ]
        self._running = False
        self._last_state: Optional[bool] = None

    def run(self):
        """Main monitoring loop."""
        self._running = True
        while self._running:
            is_online = self._check_connectivity()
            if is_online != self._last_state:
                self._last_state = is_online
                self.connectivity_changed.emit(is_online)
            time.sleep(self.check_interval)

    def stop(self):
        """Stop the monitoring thread."""
        self._running = False
        self.wait(3000)

    def _check_connectivity(self) -> bool:
        """
        Check if internet is reachable by attempting TCP connections
        to known reliable hosts.
        """
        for host, port in self.test_hosts:
            try:
                sock = socket.create_connection((host, port), timeout=self.timeout)
                sock.close()
                return True
            except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
                continue
        return False

    def force_check(self) -> bool:
        """Force an immediate connectivity check and return result."""
        return self._check_connectivity()


def is_online(timeout: int = 3) -> bool:
    """
    Synchronous one-shot connectivity check.
    Useful for quick checks without starting the monitor thread.
    """
    test_hosts = [
        ("8.8.8.8", 53),
        ("1.1.1.1", 53),
    ]
    for host, port in test_hosts:
        try:
            sock = socket.create_connection((host, port), timeout=timeout)
            sock.close()
            return True
        except (socket.timeout, socket.gaierror, ConnectionRefusedError, OSError):
            continue
    return False