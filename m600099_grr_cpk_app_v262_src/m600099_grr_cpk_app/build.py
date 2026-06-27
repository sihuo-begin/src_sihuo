#!/usr/bin/env python3
"""
Build script for M600099 GRR & CPK Analyzer.
Produces a standalone Windows executable via PyInstaller.

Usage:
    python build.py                # Build exe
    python build.py --clean        # Clean build artifacts first
    python build.py --onefile      # Build single-file exe
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
SPEC_FILE = BASE_DIR / "grr_cpk_analyzer.spec"


def run(cmd, env=None):
    print(f"\n{'='*60}\n  Running: {' '.join(str(c) for c in cmd)}\n{'='*60}")
    result = subprocess.run(cmd, env=env, cwd=str(BASE_DIR))
    if result.returncode != 0:
        print(f"[ERROR] Command failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print("[OK]")


def clean():
    dirs = [
        BASE_DIR / "build",
        BASE_DIR / "dist",
        BASE_DIR / "__pycache__",
    ]
    for d in dirs:
        if d.exists():
            shutil.rmtree(d)
            print(f"Removed: {d}")
    # Remove .spec backup files
    for f in BASE_DIR.glob("*.spec.bak"):
        f.unlink()


def install_deps():
    print("Installing dependencies…")
    run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"])


def build(onefile=False):
    install_deps()
    if onefile:
        # Single-file exe
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--name=M600099_GRR_CPK_Analyzer",
            "--onefile",
            "--windowed",       # no console window
            "--icon=NONE",
            f"--distpath={BASE_DIR / 'dist'}",
            f"--workpath={BASE_DIR / 'build'}",
            f"--specpath={BASE_DIR}",
            str(BASE_DIR / "main.py"),
        ]
    else:
        # Directory build (faster, easier to debug)
        cmd = [sys.executable, "-m", "PyInstaller", str(SPEC_FILE)]

    run(cmd)

    exe_path = BASE_DIR / "dist" / "M600099_GRR_CPK_Analyzer.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / 1024 / 1024
        print(f"\n✅ Build successful!")
        print(f"   Executable: {exe_path}")
        print(f"   Size: {size_mb:.1f} MB")
    else:
        print("\n⚠️  Exe not found – check dist/ folder.")


if __name__ == "__main__":
    if "--clean" in sys.argv:
        clean()
    if "--onefile" in sys.argv:
        build(onefile=True)
    else:
        build(onefile=False)
