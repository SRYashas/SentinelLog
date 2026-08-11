"""
SentinelLog — Python Desktop Application Entry Point
=====================================================
Checks for first-run marker file (.app_configured).
If first run -> displays modern Setup UI Popup.
If setup completes (or already configured) -> launches PyQt6 Dashboard.
"""

import sys
import os
from PyQt6.QtWidgets import QApplication

from . import bootstrapper
from . import setup_ui
from . import dashboard


def main():
    """Main application lifecycle."""
    app = QApplication(sys.argv)
    app.setApplicationName("SentinelLog")
    app.setOrganizationName("SentinelLog")

    # Check if this is the first run on a brand-new device
    if bootstrapper.is_first_run():
        print("[SentinelLog] First run detected. Launching setup UI popup...")
        setup_success = setup_ui.run_first_run_setup()
        if not setup_success:
            print("[SentinelLog] Setup failed or was cancelled. Exiting.")
            sys.exit(1)

    # Launch Main PyQt6 Dashboard Window
    print("[SentinelLog] Launching main desktop dashboard...")
    window = dashboard.DashboardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
