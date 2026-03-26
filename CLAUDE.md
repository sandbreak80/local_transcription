# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local media transcription tool using faster-whisper (CTranslate2) with GPU acceleration. All processing runs locally (no external APIs). Version 2.0.0.

Two interfaces: CLI (`transcribe.py`) and web UI + REST API (`app.py` via Flask on port 5731).

Live at https://transcript.fluximetry.com/ — API docs at /docs, GitHub at https://github.com/sandbreak80/local_transcription

## Common Commands

```bash
# Setup (installs FFmpeg + Python deps)
python setup.py

# CLI transcription
python transcribe.py <file> --model base
python transcribe.py <file> --animated-quotes
python transcribe.py <file> --two-lists
python transcribe.py <file> --speaker-diarization --speaker-names "Alice,Bob"

# Web interface
python app.py                    # starts Flask on port 5731

# Docker (with GPU)
docker build -t local-transcription .
docker run -d --gpus all -p 5731:5731 local-transcription python /app/app.py

# Tests
python tests/test_e2e.py                    # 51 E2E tests against live API
python tests/test_api_comprehensive.py      # 76 comprehensive API tests
```

## Architecture

### Core Pipeline

`transcribe.py` contains `MediaTranscriber`, which:
1. Extracts audio to WAV via `ffmpeg-python`
2. Transcribes with `faster-whisper` (CTranslate2 backend, batched inference, float16 GPU)
3. Optionally runs animated quote detection, two-list quotes, or speaker diarization
4. Saves output as WebVTT (`.vtt`) with merged speaker segments + JSON

### API Layer

`app.py` is a Flask app with:
- REST API v1 at `/api/v1/` with full CRUD for jobs
- Chunked upload support (50MB chunks) for Cloudflare Tunnel compatibility
- SQLite persistence (WAL mode) — jobs survive restarts
- Cached Whisper models in-process — no subprocess per job
- 2 parallel worker threads (configurable via `MAX_CONCURRENT_JOBS`)
- Per-job output directories for multi-user isolation
- Rate limiting (5/sec general, 30/min uploads, health exempt)
- Swagger UI API docs at `/docs` with OpenAPI 3.0 spec at `/openapi.json`

### Feature Modules

- **`animated_quotes.py`** — Voice inflection analysis using librosa prosody features. Topic classification with 3/3/4 distribution.
- **`two_list_quotes.py`** — List 1 (arbitrary 15s quotes) + List 2 (animated quotes with topic mix).
- **`local_speaker_detection.py`** — Speaker diarization via agglomerative clustering with silhouette score auto-detection. Fallback chain: speechbrain → librosa MFCC features → basic silence-gap detection.

### Key Design Patterns

- faster-whisper with `BatchedInferencePipeline` for 4-6x inference speedup
- Model cache keeps Whisper models loaded between jobs (eliminates 1-13s reload)
- Speaker count auto-detected via silhouette score (not hardcoded)
- VTT output merges consecutive same-speaker segments into readable blocks
- Chunked uploads split files into 50MB chunks for Cloudflare Tunnel (100MB limit)
- Frontend uses `escapeHtml()` for XSS protection
