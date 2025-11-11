@echo off
REM Local Transcription Tool - Web Interface Launcher (Windows)
REM Author: Brad Stoner (bmstoner@cisco.com)
REM Created for: Splunk and Cisco

setlocal EnableDelayedExpansion

set IMAGE_NAME=local-transcription-tool
if "%PORT%"=="" set PORT=5000

echo ==========================================
echo 🎙️  Local Transcription Tool - Web UI
echo ==========================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not installed or not in PATH
    echo.
    echo Please install Docker Desktop from:
    echo   https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not running
    echo.
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo ✅ Docker is ready
echo.

REM Check if image exists
docker image inspect %IMAGE_NAME% >nul 2>&1
if errorlevel 1 (
    echo 🔨 Building Docker image ^(first time only, may take 5-10 minutes^)...
    echo.
    docker build -t %IMAGE_NAME% "%~dp0"
    echo.
    echo ✅ Image built successfully!
    echo.
) else (
    echo ✅ Docker image ready
    echo.
)

echo 🌐 Starting web server on http://localhost:%PORT%
echo.
echo 📋 Instructions:
echo   1. Open your browser to http://localhost:%PORT%
echo   2. Upload your audio/video files
echo   3. Select options and start transcription
echo   4. Download results when complete
echo.
echo ⏹️  To stop: Press Ctrl+C
echo.
echo ==========================================
echo.

REM Run the container with web interface
docker run -it --rm ^
    -p %PORT%:5000 ^
    -v "%cd%\outputs:/tmp/transcription_outputs" ^
    %IMAGE_NAME% ^
    python3 /app/app.py

echo.
echo 👋 Web server stopped.
pause

