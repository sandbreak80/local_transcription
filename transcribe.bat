@echo off
REM Local Transcription Docker Wrapper for Windows
REM Usage: transcribe.bat <video_file> [options]

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker is not installed. Please install Docker Desktop for Windows.
    exit /b 1
)

REM Check if a file argument was provided
if "%~1"=="" (
    echo Usage: transcribe.bat ^<video_file^> [options]
    echo.
    echo Examples:
    echo   transcribe.bat C:\path\to\video.mp4
    echo   transcribe.bat C:\path\to\video.mp4 --model large
    echo   transcribe.bat C:\path\to\video.mp4 --animated-quotes
    echo   transcribe.bat C:\path\to\video.mp4 --two-lists
    echo.
    echo Available options:
    echo   --model ^<size^>       Whisper model (tiny^|base^|small^|medium^|large^)
    echo   --language ^<code^>    Language code (e.g., en, es, fr^)
    echo   --animated-quotes    Detect animated quotes
    echo   --two-lists          Generate two lists of quotes
    echo   --help               Show all options
    exit /b 1
)

REM Get the file path
set "FILE_PATH=%~1"

REM Check if file exists
if not exist "%FILE_PATH%" (
    echo Error: File '%FILE_PATH%' not found.
    exit /b 1
)

REM Get absolute path and directory
set "FILE_ABS_PATH=%~f1"
set "FILE_DIR=%~dp1"
set "FILE_NAME=%~nx1"

REM Remove trailing backslash from FILE_DIR if present
if "%FILE_DIR:~-1%"=="\" set "FILE_DIR=%FILE_DIR:~0,-1%"

REM Docker image name
set "IMAGE_NAME=local-transcription"

REM Check if image exists, if not build it
docker images -q %IMAGE_NAME% >nul 2>&1
if errorlevel 1 (
    echo Docker image not found. Building image...
    docker build -t %IMAGE_NAME% "%~dp0"
    if errorlevel 1 (
        echo Error: Failed to build Docker image.
        exit /b 1
    )
    echo Image built successfully!
)

REM Collect additional arguments
set "EXTRA_ARGS="
shift
:parse_args
if not "%~1"=="" (
    set "EXTRA_ARGS=%EXTRA_ARGS% %1"
    shift
    goto parse_args
)

REM Run the transcription in Docker
echo Transcribing: %FILE_NAME%
echo Output will be saved in: %FILE_DIR%
echo.

docker run --rm -v "%FILE_DIR%:/media" %IMAGE_NAME% "/media/%FILE_NAME%" %EXTRA_ARGS%

if errorlevel 1 (
    echo.
    echo X Transcription failed.
    exit /b 1
) else (
    echo.
    echo √ Transcription complete! Check %FILE_DIR% for output files.
)

