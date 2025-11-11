# Speaker Recognition Model - Embedded Setup

## Overview

This project includes an **embedded speaker recognition model** for 100% offline voice-based speaker detection. No external accounts or API tokens required!

## What's Embedded

- **Model:** speechbrain/spkrec-ecapa-voxceleb
- **Size:** ~87MB
- **Purpose:** Voice-based speaker identification
- **Location:** `models/speaker_recognition/`

## Benefits

✅ **NO downloads** - Works immediately from first use  
✅ **NO accounts** - No HuggingFace or API tokens needed  
✅ **100% offline** - Works without internet connection  
✅ **Instant startup** - Model loads in milliseconds  
✅ **Production-ready** - Perfect for distribution  

## How It Works

1. Model files are downloaded once using your HuggingFace account
2. Model is saved to `models/speaker_recognition/`
3. Docker build copies model into the image
4. Application loads model from embedded files (offline)

## Initial Setup (One-Time)

### Step 1: Download the Model

The model has already been downloaded for you! Check:

```bash
ls -lh models/speaker_recognition/
```

You should see:
- `embedding_model.ckpt` (~79MB) - Main model
- `classifier.ckpt` (~5MB) - Classifier
- `hyperparams.yaml` - Configuration
- Other supporting files

### Step 2: Build Docker Image

```bash
docker build -t local-transcription-tool .
```

The model is automatically embedded during build!

### Step 3: Verify

```bash
docker run --rm local-transcription-tool ls -lh /app/models/speaker_recognition/
```

Should show all model files inside the container.

## Updating the Model (If Needed)

If you need to update to a newer model version:

### Option 1: Automatic Download

```bash
docker run --rm \
  -v "$(pwd)/models:/app/models" \
  local-transcription-tool python3 -c "
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='speechbrain/spkrec-ecapa-voxceleb',
    local_dir='/app/models/speaker_recognition',
    local_dir_use_symlinks=False
)
"
```

### Option 2: Manual Download

1. Go to: https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb
2. Download files to `models/speaker_recognition/`
3. Rebuild Docker image

## Distribution

When sharing this project:

### Share Docker Image (Recommended)

```bash
# Save image
docker save local-transcription-tool | gzip > local-transcription-tool.tar.gz

# Load on another machine
gunzip -c local-transcription-tool.tar.gz | docker load
```

The embedded model is included - recipient needs NO setup!

### Share Source Code

If sharing source code:

1. **DO NOT** commit `models/` to git (already in .gitignore)
2. Provide `download_speaker_model.py` script
3. User runs script once to download model
4. User builds Docker image

## Troubleshooting

### Model not found

If you see "Embedded model not found, downloading...":
- Check if `models/speaker_recognition/` exists
- Verify model files are present
- Rebuild Docker image

### Permission errors

```bash
chmod -R 755 models/
```

### Large image size

- Docker image is ~3.1GB (includes PyTorch + all models)
- Worth it for offline operation + no setup
- Can be optimized further if needed

## Technical Details

### Model Architecture

- **Type:** ECAPA-TDNN (Emphasized Channel Attention, Propagation and Aggregation)
- **Training:** VoxCeleb dataset (7000+ speakers)
- **Output:** 192-dimensional speaker embeddings
- **Performance:** State-of-the-art speaker recognition

### How Speaker Detection Works

1. Extract audio segments from transcription timestamps
2. Generate voice embeddings for each segment
3. Cluster embeddings using AgglomerativeClustering
4. Assign speaker IDs based on clusters
5. Apply custom speaker names if provided

### Fallback Behavior

If embedded model fails to load:
1. Attempts to download from HuggingFace
2. If download fails, uses audio feature clustering (MFCCs)
3. Always provides some level of speaker detection

## Questions?

Contact: Brad Stoner (bmstoner@cisco.com)  
Created for: Splunk and Cisco

