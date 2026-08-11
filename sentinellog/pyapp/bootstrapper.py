"""
SentinelLog — First-Run Bootstrapper Engine
=============================================
Handles automatic detection of missing dependencies, virtual environment
creation, pip installation (offline from bundled wheels or online fallback),
database initialization, and marker file creation.

Designed to run in a background QThread so the UI stays responsive.
"""

import sys
import os
import subprocess
import shutil
import socket
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


# Paths relative to the application directory
APP_DIR = Path(__file__).parent.resolve()
VENV_DIR = APP_DIR / '.venv'
DEPS_DIR = APP_DIR / 'dependencies'
REQUIREMENTS_FILE = APP_DIR / 'requirements.txt'
MARKER_FILE = APP_DIR / '.app_configured'
ERROR_LOG = APP_DIR / 'setup_error.log'


def is_first_run():
    """Check if the app has been configured before."""
    return not MARKER_FILE.exists()


def get_venv_python():
    """Return the path to the Python executable inside the venv."""
    if os.name == 'nt':
        return str(VENV_DIR / 'Scripts' / 'python.exe')
    return str(VENV_DIR / 'Scripts' / 'python')


def get_venv_pip():
    """Return the path to pip inside the venv."""
    if os.name == 'nt':
        return str(VENV_DIR / 'Scripts' / 'pip.exe')
    return str(VENV_DIR / 'Scripts' / 'pip')


class FirstRunBootstrapper(QThread):
    """
    Background worker thread that performs the first-run setup sequence.

    Signals:
        progress_update(int): Progress percentage (0-100)
        log_message(str): Real-time log line for the setup UI
        setup_complete(): Emitted when setup finishes successfully
        setup_failed(str): Emitted with error message on failure
    """

    progress_update = pyqtSignal(int)
    log_message = pyqtSignal(str)
    setup_complete = pyqtSignal()
    setup_failed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._error_lines = []

    def run(self):
        """Execute the full setup sequence."""
        try:
            self._log("═" * 50)
            self._log("  SentinelLog — First-Run Setup")
            self._log("═" * 50)
            self._log("")

            # Step 1: Check Python (10%)
            self._step_check_python()
            self.progress_update.emit(10)

            # Step 2: Create virtual environment (30%)
            self._step_create_venv()
            self.progress_update.emit(30)

            # Step 3: Install dependencies (70%)
            self._step_install_dependencies()
            self.progress_update.emit(70)

            # Step 4: Initialize database (85%)
            self._step_init_database()
            self.progress_update.emit(85)

            # Step 5: Create marker file (100%)
            self._step_create_marker()
            self.progress_update.emit(100)

            self._log("")
            self._log("✅ Setup completed successfully!")
            self._log("   SentinelLog is ready to use.")
            self.setup_complete.emit()

        except SetupError as e:
            self._write_error_log()
            self.setup_failed.emit(str(e))
        except Exception as e:
            self._error_lines.append(f"Unexpected error: {e}")
            self._write_error_log()
            self.setup_failed.emit(f"Unexpected error during setup: {e}")

    # ── Step 1: Check Python ─────────────────────────────────────────

    def _step_check_python(self):
        self._log("🔍 Step 1/5: Checking Python environment...")

        python_version = sys.version
        self._log(f"   Python version: {python_version}")

        major, minor = sys.version_info[:2]
        if major < 3 or (major == 3 and minor < 9):
            raise SetupError(
                f"Python 3.9+ is required, but found {major}.{minor}. "
                "Please install a newer version of Python."
            )

        self._log(f"   Python executable: {sys.executable}")
        self._log("   ✓ Python version is compatible")

    # ── Step 2: Create Virtual Environment ────────────────────────────

    def _step_create_venv(self):
        self._log("")
        self._log("📦 Step 2/5: Creating isolated virtual environment...")

        if VENV_DIR.exists():
            # Check if it's a valid venv
            venv_python = get_venv_python()
            if os.path.isfile(venv_python):
                self._log(f"   ✓ Virtual environment already exists at {VENV_DIR}")
                return
            else:
                self._log("   ⚠ Existing venv appears broken. Recreating...")
                shutil.rmtree(VENV_DIR, ignore_errors=True)

        self._log(f"   Creating venv at: {VENV_DIR}")

        try:
            import venv
            builder = venv.EnvBuilder(with_pip=True, clear=True)
            builder.create(str(VENV_DIR))
        except Exception as e:
            # Fallback: use subprocess
            self._log(f"   ⚠ venv module failed ({e}), trying subprocess...")
            result = subprocess.run(
                [sys.executable, '-m', 'venv', str(VENV_DIR)],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise SetupError(
                    f"Failed to create virtual environment: {result.stderr.strip()}"
                )

        self._log("   ✓ Virtual environment created successfully")

    # ── Step 3: Install Dependencies ──────────────────────────────────

    def _step_install_dependencies(self):
        self._log("")
        self._log("📥 Step 3/5: Installing dependencies...")

        pip_path = get_venv_pip()
        if not os.path.isfile(pip_path):
            # Try to bootstrap pip
            self._log("   ⚠ pip not found in venv. Bootstrapping...")
            result = subprocess.run(
                [get_venv_python(), '-m', 'ensurepip', '--upgrade'],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                raise SetupError("Could not install pip in the virtual environment.")

        # Upgrade pip first
        self._log("   Upgrading pip...")
        self._run_pip(['install', '--upgrade', 'pip'])

        # Check for bundled wheel files (Option A: True Offline)
        has_local_wheels = DEPS_DIR.exists() and any(DEPS_DIR.glob('*.whl'))

        if has_local_wheels:
            self._log("   📂 Found local wheel files — installing offline")
            self._install_from_local_wheels()
        elif self._check_internet():
            self._log("   🌐 No local wheels found — downloading from internet")
            self._install_from_internet()
        else:
            raise SetupError(
                "No local dependency files found and no internet connection available.\n\n"
                "To fix this:\n"
                "1. On an internet-connected machine, run:\n"
                "   pip download -r requirements.txt -d dependencies/\n"
                "2. Copy the 'dependencies/' folder to this machine.\n"
                "3. Re-run the setup."
            )

        self._log("   ✓ All dependencies installed")

    def _install_from_local_wheels(self):
        """Install from pre-downloaded .whl files in dependencies/ folder."""
        whl_files = list(DEPS_DIR.glob('*.whl')) + list(DEPS_DIR.glob('*.tar.gz'))
        self._log(f"   Found {len(whl_files)} package files")

        # Install all wheels at once
        self._run_pip([
            'install',
            '--no-index',
            f'--find-links={DEPS_DIR}',
            '-r', str(REQUIREMENTS_FILE)
        ])

    def _install_from_internet(self):
        """Install dependencies from PyPI (online fallback)."""
        if REQUIREMENTS_FILE.exists():
            self._run_pip(['install', '-r', str(REQUIREMENTS_FILE)])
        else:
            # Install core packages directly
            packages = ['PyQt6', 'python-evtx', 'pandas', 'pyqtgraph', 'lxml']
            for pkg in packages:
                self._log(f"   Installing {pkg}...")
                self._run_pip(['install', pkg])

    def _run_pip(self, args):
        """Run a pip command inside the venv and stream output to the UI."""
        pip_path = get_venv_pip()
        cmd = [pip_path] + args

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            for line in process.stdout:
                line = line.strip()
                if line:
                    # Show key pip output lines
                    if any(kw in line.lower() for kw in ['installing', 'collecting', 'downloading',
                                                          'successfully', 'requirement', 'building']):
                        self._log(f"   → {line}")

            process.wait()

            if process.returncode != 0:
                raise SetupError(f"pip command failed with exit code {process.returncode}")

        except FileNotFoundError:
            raise SetupError("pip executable not found. Virtual environment may be corrupted.")

    def _check_internet(self):
        """Quick check for internet connectivity."""
        try:
            socket.setdefaulttimeout(3)
            socket.create_connection(('pypi.org', 443))
            return True
        except (socket.timeout, OSError):
            return False

    # ── Step 4: Initialize Database ───────────────────────────────────

    def _step_init_database(self):
        self._log("")
        self._log("🗄️  Step 4/5: Initializing local SQLite database...")

        try:
            # Import our db module directly (it uses stdlib sqlite3)
            from . import db
            db.init_database()
            db_path = db.get_db_path()
            self._log(f"   Database location: {db_path}")
            self._log("   ✓ Database initialized with schema and default threat rules")
        except Exception as e:
            raise SetupError(f"Failed to initialize database: {e}")

    # ── Step 5: Create Marker File ────────────────────────────────────

    def _step_create_marker(self):
        self._log("")
        self._log("🏁 Step 5/5: Finalizing configuration...")

        try:
            from datetime import datetime
            MARKER_FILE.write_text(
                f"configured_at={datetime.now().isoformat()}\n"
                f"python={sys.version}\n"
                f"platform={sys.platform}\n"
            )
            self._log(f"   Marker file created at: {MARKER_FILE}")
            self._log("   ✓ First-run setup completed")
        except Exception as e:
            raise SetupError(f"Failed to create configuration marker: {e}")

    # ── Helpers ───────────────────────────────────────────────────────

    def _log(self, message):
        """Emit a log message to the UI."""
        self._error_lines.append(message)
        self.log_message.emit(message)

    def _write_error_log(self):
        """Write accumulated log to error log file."""
        try:
            ERROR_LOG.write_text('\n'.join(self._error_lines))
        except Exception:
            pass


class SetupError(Exception):
    """Custom exception for setup failures."""
    pass
