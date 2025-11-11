# Use Python slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (FFmpeg and other required tools)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY transcribe.py .
COPY animated_quotes.py .
COPY two_list_quotes.py .
COPY app.py .

# Copy web interface files
COPY templates ./templates
COPY static ./static

# Create directories
RUN mkdir -p /media /tmp/transcription_uploads /tmp/transcription_outputs

# Expose port for web interface
EXPOSE 5731

# Set the entrypoint to python transcribe script
ENTRYPOINT ["python", "/app/transcribe.py"]

# Default command shows help
CMD ["--help"]

