#!/usr/bin/env python3
"""
Dependency checker script for sub-tools.
This script checks if all required system dependencies are installed.
"""

import os
import subprocess
import sys
import importlib.util
from pathlib import Path

def check_command(command, name=None):
    """Check if a command is available."""
    name = name or command
    try:
        subprocess.run([command, "--version"], 
                      stdout=subprocess.PIPE, 
                      stderr=subprocess.PIPE, 
                      check=True)
        print(f"✅ {name} is installed")
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print(f"❌ {name} is NOT installed")
        return False

def check_python_package(package):
    """Check if a Python package is installed."""
    try:
        importlib.import_module(package)
        print(f"✅ Python package '{package}' is installed")
        return True
    except ImportError:
        print(f"❌ Python package '{package}' is NOT installed")
        return False

def main():
    """Main function."""
    print("Checking system dependencies for sub-tools:")
    
    # Check system commands
    ffmpeg_installed = check_command("ffmpeg")
    
    # Check Python packages
    pydub_installed = check_python_package("pydub")
    silero_vad_installed = check_python_package("silero_vad")
    soundfile_installed = check_python_package("soundfile")
    pysrt_installed = check_python_package("pysrt")
    
    # Summary
    print("\nSummary:")
    all_installed = all([
        ffmpeg_installed, 
        pydub_installed,
        silero_vad_installed,
        soundfile_installed,
        pysrt_installed
    ])
    
    if all_installed:
        print("🎉 All dependencies are installed!")
    else:
        print("⚠️  Some dependencies are missing. Please install them to use sub-tools properly.")
        
        if not ffmpeg_installed:
            print("  - Install FFmpeg: https://ffmpeg.org/download.html")
            print("    Ubuntu/Debian: sudo apt-get install ffmpeg")
            print("    macOS: brew install ffmpeg")
        
        missing_packages = []
        if not pydub_installed:
            missing_packages.append("pydub")
        if not silero_vad_installed:
            missing_packages.append("silero-vad")
        if not soundfile_installed:
            missing_packages.append("soundfile")
        if not pysrt_installed:
            missing_packages.append("pysrt")
            
        if missing_packages:
            packages_str = " ".join(missing_packages)
            print(f"  - Install Python packages: pip install {packages_str}")
            print("    You may also need system libraries for audio processing:")
            print("    Ubuntu/Debian: sudo apt-get install libasound2-dev")
            print("    macOS: brew install portaudio")
    
    return 0 if all_installed else 1

if __name__ == "__main__":
    sys.exit(main())