#!/bin/bash

# Local Transcription Tool - Web Interface Launcher (Mac/Linux)
# Local Transcription Tool - Web Interface Launcher

set -e

IMAGE_NAME="local-transcription-tool"
PORT="${PORT:-5731}"

echo "=========================================="
echo "🎙️  Local Transcription Tool - Web UI"
echo "=========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Error: Docker is not installed or not in PATH"
    echo ""
    echo "Please install Docker Desktop from:"
    echo "  https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Error: Docker is not running"
    echo ""
    echo "Please start Docker Desktop and try again."
    exit 1
fi

echo "✅ Docker is ready"
echo ""

# Check if image exists
if ! docker image inspect "$IMAGE_NAME" &> /dev/null; then
    echo "🔨 Building Docker image (first time only, may take 5-10 minutes)..."
    echo ""
    docker build -t "$IMAGE_NAME" "$(dirname "$0")"
    echo ""
    echo "✅ Image built successfully!"
    echo ""
else
    echo "✅ Docker image ready"
    echo ""
fi

echo "🌐 Starting web server on http://localhost:$PORT"
echo ""
echo "📋 Instructions:"
echo "  • Browser will open automatically in 3 seconds..."
echo "  • Upload your audio/video files"
echo "  • Select options and start transcription"
echo "  • Download results when complete"
echo ""
echo "⏹️  To stop: Press Ctrl+C"
echo ""
echo "=========================================="
echo ""

# Function to open browser after a delay
open_browser() {
    sleep 3
    echo "🌐 Opening browser..."
    
    # Detect OS and open browser accordingly
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        open "http://localhost:$PORT"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v xdg-open &> /dev/null; then
            xdg-open "http://localhost:$PORT"
        elif command -v gnome-open &> /dev/null; then
            gnome-open "http://localhost:$PORT"
        fi
    fi
}

# Start browser opener in background
open_browser &

# Enable GPU if nvidia-smi is available
GPU_FLAG=""
if command -v nvidia-smi &> /dev/null && docker info 2>/dev/null | grep -q nvidia; then
    GPU_FLAG="--gpus all"
    echo "🚀 GPU acceleration enabled"
fi

# Run the container with web interface
docker run -it --rm \
    $GPU_FLAG \
    -p "$PORT:5731" \
    -e "FLASK_PORT=5731" \
    -v "$(pwd)/outputs:/tmp/transcription_outputs" \
    "$IMAGE_NAME" \
    python3 /app/app.py

echo ""
echo "👋 Web server stopped."

