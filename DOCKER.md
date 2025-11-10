# Docker Setup Guide

This guide explains how to use the Local Media Transcription Tool with Docker.

## Why Docker?

Docker provides several benefits:

- ✅ **Zero Setup**: No need to install Python, FFmpeg, or any dependencies
- ✅ **Consistent Environment**: Works the same on macOS, Windows, and Linux
- ✅ **Easy Sharing**: Share the tool with colleagues - they just need Docker
- ✅ **Isolated**: Doesn't interfere with your system's Python installation
- ✅ **Portable**: Easy to deploy on servers or cloud platforms

## Installation

### 1. Install Docker

Download and install Docker Desktop for your platform:
- [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- [Docker for Linux](https://docs.docker.com/engine/install/)

### 2. Get the Tool

Clone or download this repository:

```bash
git clone <your-repo-url>
cd local-transcription
```

## Quick Start

### macOS/Linux

The easiest way is to use the provided shell script:

```bash
# Make it executable (first time only)
chmod +x transcribe.sh

# Transcribe a video
./transcribe.sh /path/to/video.mp4

# With options
./transcribe.sh /path/to/video.mp4 --model large --animated-quotes
```

### Windows

Use the batch file:

```cmd
transcribe.bat C:\path\to\video.mp4

REM With options
transcribe.bat C:\path\to\video.mp4 --model large --animated-quotes
```

## Manual Docker Commands

If you prefer more control, you can use Docker commands directly:

### Build the Image

```bash
docker build -t local-transcription .
```

This creates a Docker image named `local-transcription` with all dependencies.

### Run Transcription

Basic syntax:

```bash
docker run --rm -v "/path/to/video/folder:/media" local-transcription /media/video.mp4
```

Breakdown:
- `docker run` - Run a container
- `--rm` - Remove container after completion
- `-v "/path/to/video/folder:/media"` - Mount your video folder to `/media` in the container
- `local-transcription` - The image name
- `/media/video.mp4` - Path to your video inside the container

### Examples

**Basic transcription:**

```bash
docker run --rm \
  -v "$HOME/Videos:/media" \
  local-transcription \
  /media/presentation.mp4
```

**With larger model:**

```bash
docker run --rm \
  -v "$HOME/Videos:/media" \
  local-transcription \
  /media/presentation.mp4 \
  --model large
```

**Animated quotes:**

```bash
docker run --rm \
  -v "$HOME/Videos:/media" \
  local-transcription \
  /media/presentation.mp4 \
  --animated-quotes
```

**Specify language:**

```bash
docker run --rm \
  -v "$HOME/Videos:/media" \
  local-transcription \
  /media/spanish-video.mp4 \
  --language es
```

## Using Docker Compose

For recurring use, you can use docker-compose:

```bash
# Build the image
docker-compose build

# Show help
docker-compose run --rm transcribe --help

# Transcribe a file (place video in ./media folder)
docker-compose run --rm transcribe /media/video.mp4

# With options
docker-compose run --rm transcribe /media/video.mp4 --model large

# Use custom volume
docker-compose run --rm \
  -v /path/to/your/videos:/media \
  transcribe /media/video.mp4
```

## Output Files

All output files are automatically saved to the same directory as your input video:

- `videoname_transcription.txt` - Plain text transcript with timestamps
- `videoname_transcription.json` - Detailed JSON with segments and metadata
- `videoname_animated_quotes.txt` - Animated quotes (if requested)
- `videoname_animated_quotes.json` - Animated quotes in JSON format
- `videoname_two_list_quotes.txt` - Two lists of quotes (if requested)

## Troubleshooting

### "Docker is not installed"

Make sure Docker Desktop is running. On macOS, check your menu bar. On Windows, check the system tray.

### "File not found"

Make sure you're using the full absolute path to your video file:

```bash
# Good
./transcribe.sh /Users/username/Videos/video.mp4

# Bad
./transcribe.sh ~/Videos/video.mp4  # ~ might not expand
./transcribe.sh Videos/video.mp4     # relative paths might fail
```

### "Permission denied"

On macOS/Linux, make sure the script is executable:

```bash
chmod +x transcribe.sh
```

### Slow First Run

The first time you run a transcription, Whisper downloads the model (~75MB for base, ~1.5GB for large). Subsequent runs are much faster as the model is cached.

### Out of Memory

If you run out of memory:
- Use a smaller model: `--model tiny` or `--model base`
- Close other applications
- Increase Docker's memory limit in Docker Desktop preferences

### Image Takes Too Long to Build

Building the Docker image the first time takes 5-10 minutes as it installs all dependencies. This only happens once. If you need to rebuild:

```bash
# Quick rebuild (uses cache)
docker build -t local-transcription .

# Full rebuild (no cache)
docker build -t local-transcription . --no-cache
```

## Advanced Usage

### Running in the Background

For very long videos, you can detach the process:

```bash
docker run -d \
  --name my-transcription \
  -v "$HOME/Videos:/media" \
  local-transcription \
  /media/long-video.mp4 \
  --model large

# Check progress
docker logs -f my-transcription

# Stop if needed
docker stop my-transcription
```

### Batch Processing

To transcribe all videos in a folder:

```bash
docker run --rm \
  -v "$HOME/Videos:/media" \
  local-transcription \
  /media \
  --batch \
  --recursive
```

### Using on a Server

Deploy on a server with Docker:

```bash
# Pull your image (if hosted)
docker pull your-registry/local-transcription

# Or build locally
docker build -t local-transcription .

# Run with volume mount
docker run --rm \
  -v /mnt/videos:/media \
  local-transcription \
  /media/video.mp4 \
  --model large
```

### GPU Support

For GPU acceleration (requires NVIDIA GPU and nvidia-docker):

1. Modify the Dockerfile to use a CUDA base image:
```dockerfile
FROM nvidia/cuda:11.8.0-base-ubuntu22.04
```

2. Run with GPU support:
```bash
docker run --rm --gpus all \
  -v "$HOME/Videos:/media" \
  local-transcription \
  /media/video.mp4
```

## Sharing with Others

To share this tool with colleagues:

### Option 1: Share the Repository

Simply share this repository. They just need to:
1. Install Docker
2. Clone the repository
3. Run `./transcribe.sh` (macOS/Linux) or `transcribe.bat` (Windows)

### Option 2: Share the Docker Image

Build and share the image:

```bash
# Save image to file
docker save local-transcription > local-transcription.tar

# Share the .tar file, then they can load it:
docker load < local-transcription.tar
```

### Option 3: Host on Docker Hub

Push to Docker Hub for easy distribution:

```bash
# Tag the image
docker tag local-transcription your-username/local-transcription

# Push to Docker Hub
docker push your-username/local-transcription

# Others can pull and use:
docker pull your-username/local-transcription
```

## Resource Management

### Cleaning Up

Remove unused containers and images:

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove everything (careful!)
docker system prune -a
```

### Checking Resource Usage

```bash
# See running containers
docker ps

# Check resource usage
docker stats

# See disk usage
docker system df
```

## Support

If you encounter issues:

1. Check that Docker is running: `docker --version`
2. Verify the video file exists: `ls -la /path/to/video.mp4`
3. Try with a smaller model first: `--model tiny`
4. Check Docker logs: `docker logs <container-id>`
5. Rebuild the image: `docker build -t local-transcription . --no-cache`

