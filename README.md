# Local Transcription Tool

AI-powered audio & video transcription using [faster-whisper](https://github.com/SYSTRAN/faster-whisper) with GPU acceleration. All processing runs locally — no data leaves your machine.

**Version:** 2.0.0 | **Live:** [transcript.fluximetry.com](https://transcript.fluximetry.com/) | **API Docs:** [Swagger UI](https://transcript.fluximetry.com/docs) | **Output:** WebVTT (.vtt)

---

## Performance

Benchmarked on RTX 4070 with 65-minute audiobook (LibriSpeech test-clean):

| Model | Time | Speed | Avg WER |
|-------|------|-------|---------|
| tiny | 72s | 54x realtime | ~5.3% |
| base | 48s | 81x realtime | 4.7% |
| **small** | **51s** | **76x realtime** | **4.0%** |
| medium | 78s | 50x realtime | 3.3% |

- **WER** measured against LibriSpeech test-clean (10 speakers, ground truth transcripts)
- **Batched inference** via CTranslate2 — up to 5.8x faster than openai-whisper
- **Model caching** — models stay loaded between jobs, eliminating 1-13s reload overhead
- **GPU acceleration** with automatic CPU fallback on CUDA OOM

## Features

- **20+ formats** — MP4, MP3, WAV, AVI, MOV, MKV, FLAC, OGG, WebM, M4A, and more
- **REST API** — Full CRUD at `/api/v1/` with OpenAPI 3.0 spec
- **Chunked uploads** — 50MB chunks for Cloudflare Tunnel compatibility (100MB limit)
- **Speaker detection** — ECAPA-TDNN neural embeddings with silhouette score auto-detection
- **WebVTT output** — Industry-standard subtitle format with speaker voice tags
- **Multi-user** — Per-job output isolation, 2 parallel workers, SQLite persistence
- **Web UI** — Drag & drop, real-time progress, toggle switches for features
- **Docker + GPU** — `--gpus all` support in all scripts and docker-compose

## Quick Start

### Docker (recommended)

```bash
docker build -t local-transcription .
docker run -d --gpus all -p 5731:5731 local-transcription python /app/app.py
```

Open http://localhost:5731

### Python

```bash
python setup.py          # Install FFmpeg + dependencies
python app.py            # Start web UI + API on port 5731
```

### CLI

```bash
python transcribe.py meeting.mp4 --model small --speaker-diarization
python transcribe.py podcast.mp3 --model medium --language en
python transcribe.py folder/ --batch --recursive --output-dir ./output
```

## API

Full documentation at [/docs](https://transcript.fluximetry.com/docs) (Swagger UI).

### Upload and transcribe

```bash
curl -X POST https://transcript.fluximetry.com/api/v1/jobs \
  -F "files=@meeting.mp4" \
  -F "model=small" \
  -F "speaker_diarization=true"
```

### Check status

```bash
curl https://transcript.fluximetry.com/api/v1/jobs/{job_id}
```

### Download result

```bash
curl -O https://transcript.fluximetry.com/api/v1/jobs/{job_id}/files/meeting.vtt
```

### Chunked upload (large files)

```bash
# 1. Initiate
curl -X POST /api/v1/uploads \
  -H "Content-Type: application/json" \
  -d '{"filename":"large.mp4","total_chunks":6,"model":"small"}'

# 2. Upload chunks
curl -X POST /api/v1/uploads/{id}/chunks -F "chunk=@chunk_0" -F "chunk_index=0"

# 3. Finalize
curl -X POST /api/v1/uploads/{id}/complete
```

## n8n Workflows

Ready-to-import automation workflows in the [`workflows/`](workflows/) directory:

| Workflow | Description |
|----------|-------------|
| [`transcribe-and-email.json`](workflows/transcribe-and-email.json) | Upload file, transcribe, email the VTT result |
| [`watch-folder.json`](workflows/watch-folder.json) | Monitor a folder, auto-transcribe new files |
| [`meeting-minutes.json`](workflows/meeting-minutes.json) | Transcribe with speakers, generate meeting summary via LLM |
| [`multi-language.json`](workflows/multi-language.json) | Detect language, transcribe, translate to English |
| [`webhook-pipeline.json`](workflows/webhook-pipeline.json) | Receive files via webhook, transcribe, POST results back |

Import any workflow into n8n: **Settings > Import from File**

## Limitations & Known Issues

### Limitations

- **Speaker detection on single-narrator audio** — One person doing character voices (audiobooks, dramatic readings) will cluster as 1-2 speakers. This is a fundamental limitation of voice-based diarization; the same vocal tract produces similar embeddings regardless of character voice. Multi-speaker recordings (meetings, interviews) work well.
- **Large model requires ~10GB VRAM** — On a 12GB GPU with other processes, the `large` model may OOM and fall back to CPU, which is very slow. Use `small` or `medium` instead.
- **No real-time streaming** — Files must be uploaded in full before processing starts.
- **No authentication** — The API has rate limiting but no user auth. Intended for trusted networks or behind a reverse proxy with auth.

### Known Issues

- Progress stays at 20% during transcription — no incremental progress from Whisper
- `--batch` mode ignores `--animated-quotes` and `--speaker-diarization` flags
- VTT speaker tags use generic `SPEAKER_00` / `SPEAKER_01` labels unless `--speaker-names` is provided
- Animated quote topic classification is tuned for enterprise/technology content

## Roadmap

- [ ] **Streaming transcription** — Start returning results before the full file is processed
- [ ] **Whisper large-v3 turbo** — Smaller, faster large model when CTranslate2 adds support
- [ ] **Multi-GPU support** — Distribute jobs across multiple GPUs
- [ ] **Webhook notifications** — POST job status to a callback URL on completion
- [ ] **User authentication** — API key or OAuth for multi-tenant deployments
- [ ] **S3/MinIO storage** — Store outputs in object storage instead of local disk
- [ ] **Job retention policy** — Auto-cleanup completed jobs after configurable TTL
- [ ] **Real-time progress** — WebSocket or SSE for live transcription progress

## Testing

```bash
# Functional + edge case tests (77 tests)
python tests/test_api_comprehensive.py

# Accuracy validation (WER, speaker detection, VTT format)
python tests/test_accuracy.py

# Basic E2E tests (51 tests)
python tests/test_e2e.py
```

## License

MIT
