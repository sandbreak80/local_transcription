# Use CUDA-enabled base image for GPU acceleration
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y python3.11 python3.11-dev python3-pip && \
    ln -sf python3.11 /usr/bin/python3 && ln -sf python3 /usr/bin/python && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install system dependencies (FFmpeg and other required tools)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install PyTorch with CUDA 12.1 support first (must come before requirements.txt)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install remaining Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY transcribe.py .
COPY animated_quotes.py .
COPY two_list_quotes.py .
COPY speaker_diarization.py .
COPY local_speaker_detection.py .
COPY app.py .

# Copy embedded speaker recognition model (NO downloads needed!)
COPY models ./models

# Copy web interface files
COPY templates ./templates
COPY static ./static

# Create directories
RUN mkdir -p /media /tmp/transcription_uploads /tmp/transcription_outputs

# Expose port for web interface
EXPOSE 5731

# No default entrypoint - allows running either CLI or web interface
# For CLI: docker run ... python /app/transcribe.py [options]
# For Web: docker run ... python /app/app.py

