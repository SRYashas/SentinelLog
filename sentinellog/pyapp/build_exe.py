"""
SentinelLog — PyInstaller Standalone .EXE Builder
===================================================
Compiles SentinelLog and all its dependencies into a standalone Windows .exe file.
End-users can run this on any Windows PC without having Python or any packages installed.

Usage:
  python build_exe.py
"""

import sys
import os
import subprocess
import shutil
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
ENTRY_POINT = APP_DIR / 'main.py'
DIST_DIR = APP_DIR.parent / 'dist-py'
BUILD_DIR = APP_DIR / 'build'


def build_standalone_exe():
    """Invoke PyInstaller to generate the standalone .exe file."""
    print("==================================================")
    print("  SentinelLog — Compiling Standalone .EXE")
    print("==================================================")
    print("")

    # Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("📦 Installing PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], check=True)

    # Build PyInstaller command options
    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--name=SentinelLog',
        '--onefile',                       # Single executable file
        '--windowed',                      # Hide console window
        '--clean',
        f'--distpath={DIST_DIR}',
        f'--workpath={BUILD_DIR}',
        '--add-data=' + str(APP_DIR / 'requirements.txt') + ';pyapp',
    ]

    # Include dependencies folder if present
    deps_folder = APP_DIR / 'dependencies'
    if deps_folder.exists():
        cmd.append(f'--add-data={deps_folder};pyapp/dependencies')

    # Hidden imports needed by PyQt6 & libraries
    hidden_imports = [
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'pyqtgraph',
        'Evtx.Evtx',
        'Evtx.Views',
        'lxml',
        'sqlite3',
        'json',
        'xml.etree.ElementTree'
    ]

    for imp in hidden_imports:
        cmd.append(f'--hidden-import={imp}')

    # Target script
    cmd.append(str(ENTRY_POINT))

    print(f"🚀 Running PyInstaller...")
    print(f"   Cmd: {' '.join(cmd)}")
    print("")

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = DIST_DIR / 'SentinelLog.exe'
        print("")
        print("==================================================")
        print("🎉 SUCCESS! Standalone executable created:")
        print(f"   Path: {exe_path}")
        print("==================================================")
        print("This .exe can be copied to ANY Windows PC and run directly")
        print("without installing Python or any dependencies!")
    else:
        print("")
        print("❌ PyInstaller compilation failed. Check logs above.")


if __name__ == '__main__':
    build_standalone_exe()
