"""
SentinelLog — Offline Wheel Downloader
=======================================
Pre-downloads all wheel (.whl) package files into pyapp/dependencies/
so that the application can install 100% offline on clean Windows devices.

Usage:
  python download_wheels.py
"""

import sys
import os
import subprocess
from pathlib import Path

APP_DIR = Path(__file__).parent.resolve()
DEPS_DIR = APP_DIR / 'dependencies'
REQUIREMENTS_FILE = APP_DIR / 'requirements.txt'


def download_wheels():
    """Download all required wheel files into dependencies/ folder."""
    DEPS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📦 Downloading wheel files into: {DEPS_DIR}")
    print(f"   Requirements file: {REQUIREMENTS_FILE}")
    print("")

    cmd = [
        sys.executable, '-m', 'pip', 'download',
        '-r', str(REQUIREMENTS_FILE),
        '-d', str(DEPS_DIR),
        '--only-binary=:all:',  # Prefer pre-built binaries (.whl)
        '--platform', 'win_amd64',
        '--python-version', '311',
        '--no-deps'
    ]

    # Run pip download
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("")
        print("✅ All wheel files downloaded successfully!")
        wheels = list(DEPS_DIR.glob('*'))
        print(f"   Total packages downloaded: {len(wheels)}")
        for w in wheels:
            print(f"   - {w.name}")
    else:
        print("⚠️ Direct win_amd64 download failed, falling back to standard pip download...")
        fallback_cmd = [
            sys.executable, '-m', 'pip', 'download',
            '-r', str(REQUIREMENTS_FILE),
            '-d', str(DEPS_DIR)
        ]
        subprocess.run(fallback_cmd)


if __name__ == '__main__':
    download_wheels()
