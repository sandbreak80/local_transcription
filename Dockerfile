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
# RTX 5070 (Blackwell, sm_120) needs torch built for CUDA 12.8; install before requirements.txt.
RUN pip install --no-cache-dir torch==2.7.1 torchaudio==2.7.1 --index-url https://download.pytorch.org/whl/cu128

RUN pip install --no-cache-dir -r requirements.txt

# faster-whisper (CTranslate2) loads cuBLAS/cuDNN by soname; point it at the pip-installed CUDA libs.
ENV LD_LIBRARY_PATH=/usr/local/lib/python3.11/site-packages/nvidia/cublas/lib:/usr/local/lib/python3.11/site-packages/nvidia/cudnn/lib

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

