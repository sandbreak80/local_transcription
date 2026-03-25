#!/bin/bash

# Local Transcription Docker Wrapper
# Usage: ./transcribe.sh <video_file> [options]

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if a file argument was provided
if [ $# -eq 0 ]; then
    echo "Usage: ./transcribe.sh <video_file> [options]"
    echo ""
    echo "Examples:"
    echo "  ./transcribe.sh /path/to/video.mp4"
    echo "  ./transcribe.sh /path/to/video.mp4 --model large"
    echo "  ./transcribe.sh /path/to/video.mp4 --animated-quotes"
    echo "  ./transcribe.sh /path/to/video.mp4 --two-lists"
    echo ""
    echo "Available options:"
    echo "  --model <size>       Whisper model (tiny|base|small|medium|large)"
    echo "  --language <code>    Language code (e.g., en, es, fr)"
    echo "  --animated-quotes    Detect animated quotes"
    echo "  --two-lists          Generate two lists of quotes"
    echo "  --help               Show all options"
    exit 1
fi

# Get the first argument (the file path)
FILE_PATH="$1"
shift

# Check if file exists
if [ ! -f "$FILE_PATH" ]; then
    echo "Error: File '$FILE_PATH' not found."
    exit 1
fi

# Get absolute path of the file
FILE_ABS_PATH=$(cd "$(dirname "$FILE_PATH")" && pwd)/$(basename "$FILE_PATH")

# Get the directory containing the file
FILE_DIR=$(dirname "$FILE_ABS_PATH")

# Get just the filename
FILE_NAME=$(basename "$FILE_ABS_PATH")

# Docker image name
IMAGE_NAME="local-transcription"

# Check if image exists, if not build it
if [[ "$(docker images -q $IMAGE_NAME 2> /dev/null)" == "" ]]; then
    echo "Docker image not found. Building image..."
    SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    docker build -t $IMAGE_NAME "$SCRIPT_DIR"
    
    if [ $? -ne 0 ]; then
        echo "Error: Failed to build Docker image."
        exit 1
    fi
    echo "Image built successfully!"
fi

# Run the transcription in Docker
echo "Transcribing: $FILE_NAME"
echo "Output will be saved in: $FILE_DIR"
echo ""

# Enable GPU if nvidia-smi is available
GPU_FLAG=""
if command -v nvidia-smi &> /dev/null && docker info 2>/dev/null | grep -q nvidia; then
    GPU_FLAG="--gpus all"
    echo "🚀 GPU acceleration enabled"
fi

docker run --rm \
    $GPU_FLAG \
    -v "$FILE_DIR:/media" \
    $IMAGE_NAME \
    "/media/$FILE_NAME" \
    "$@"

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Transcription complete! Check $FILE_DIR for output files."
else
    echo ""
    echo "✗ Transcription failed."
    exit 1
fi

