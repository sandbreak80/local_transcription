# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Local media transcription tool using OpenAI's Whisper model. All processing runs locally (no external APIs). Built for Cisco/Splunk by Brad Stoner. Version 1.2.0.

Two interfaces: CLI (`transcribe.py`) and web UI (`app.py` via Flask on port 5731).

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

# Docker
./transcribe.sh <file>           # CLI via Docker
./transcribe-web.sh              # Web UI via Docker
docker build -t local-transcription .

# Tests (manual, no test framework)
python test_animated_quotes.py   # requires a test audio file
```

There is no automated test suite, linter, or CI pipeline configured.

## Architecture

### Core Pipeline

`transcribe.py` is the main entry point (CLI via `click`). It contains `MediaTranscriber`, which:
1. Extracts audio to WAV via `ffmpeg-python`
2. Transcribes with `whisper.load_model()` / `model.transcribe()`
3. Optionally runs animated quote detection, two-list quotes, or speaker diarization
4. Saves output as `_transcription.txt` / `.json` (plus quote/speaker files)

### Feature Modules

- **`animated_quotes.py`** - `AnimatedQuoteDetector`: analyzes voice inflection using librosa prosody features (RMS, spectral centroid, ZCR, MFCC, pitch). Classifies into 3 Cisco-specific topic categories (current_state, future_direction, product_pipeline) via keyword/pattern matching. Selects top quotes with 3/3/4 topic distribution.

- **`two_list_quotes.py`** - `TwoListQuoteDetector`: produces List 1 (arbitrary 15s quotes, evenly distributed) and List 2 (animated quotes with 30% topic mix per category).

- **`local_speaker_detection.py`** - `LocalSpeakerDetector`: speaker diarization using speechbrain ECAPA-TDNN embeddings with agglomerative clustering fallback to librosa MFCC features. No external accounts needed. Model stored in `models/speaker_recognition/`.

- **`speaker_diarization.py`** - `SpeakerDiarizer`: alternative diarization via `pyannote.audio` (requires HuggingFace token). Not used by default; `local_speaker_detection.py` is preferred.

### Web Interface

`app.py` is a Flask app that wraps the CLI. It spawns `transcribe.py` as a subprocess, manages a job queue with a background worker thread, and stores state in an in-memory `jobs` dict. Uploaded files go to `/tmp/transcription_uploads`, outputs to `/tmp/transcription_outputs`. The web frontend is a single `templates/index.html` file.

### Key Design Patterns

- Speaker detection has a graceful fallback chain: speechbrain -> librosa feature clustering -> basic silence-gap detection
- Audio is always converted to 16kHz mono WAV before processing
- The web app shells out to `transcribe.py` rather than importing it as a library
- Topic classification is hardcoded for Cisco AI content categories
