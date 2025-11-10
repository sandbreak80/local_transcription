#!/usr/bin/env python3
"""
Setup script for Local Media Transcription Tool
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"  Error: {e.stderr}")
        return False


def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        print("✓ FFmpeg is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ FFmpeg is not installed")
        return False


def install_ffmpeg_macos():
    """Install FFmpeg on macOS using Homebrew."""
    print("\nInstalling FFmpeg using Homebrew...")
    
    # Check if Homebrew is installed
    try:
        subprocess.run(['brew', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Homebrew is not installed. Please install Homebrew first:")
        print("  /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
        return False
    
    # Install FFmpeg
    return run_command('brew install ffmpeg', 'Installing FFmpeg')


def main():
    """Main setup function."""
    print("🎵 Local Media Transcription Tool Setup")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Check if FFmpeg is installed
    if not check_ffmpeg():
        if sys.platform == "darwin":  # macOS
            if not install_ffmpeg_macos():
                print("\nPlease install FFmpeg manually and run this setup again.")
                sys.exit(1)
        else:
            print("\nPlease install FFmpeg for your system:")
            print("  Ubuntu/Debian: sudo apt install ffmpeg")
            print("  CentOS/RHEL: sudo yum install ffmpeg")
            print("  Windows: Download from https://ffmpeg.org/download.html")
            sys.exit(1)
    
    # Install Python dependencies
    print("\nInstalling Python dependencies...")
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", 
                      "Installing Python packages"):
        print("Failed to install Python dependencies")
        sys.exit(1)
    
    # Make the script executable
    script_path = Path(__file__).parent / "transcribe.py"
    if script_path.exists():
        os.chmod(script_path, 0o755)
        print("✓ Made transcribe.py executable")
    
    print("\n🎉 Setup completed successfully!")
    print("\nUsage examples:")
    print("  python transcribe.py audio_file.mp3")
    print("  python transcribe.py video_file.mp4 --model large")
    print("  python transcribe.py /path/to/folder --batch")
    print("  python transcribe.py --help")


if __name__ == "__main__":
    main()