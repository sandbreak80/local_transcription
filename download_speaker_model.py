#!/usr/bin/env python3
"""
Download speechbrain speaker recognition model for embedding in Docker image.
Run this ONCE on your machine, then the model is included in the Docker build.

Usage:
    python3 download_speaker_model.py

Author: Brad Stoner (bmstoner@cisco.com)
"""

import os
from pathlib import Path

try:
    from speechbrain.inference.speaker import EncoderClassifier
    print("✅ speechbrain is installed")
except ImportError:
    print("❌ speechbrain not installed. Installing...")
    os.system("pip install speechbrain")
    from speechbrain.inference.speaker import EncoderClassifier

# Create models directory
models_dir = Path(__file__).parent / "models" / "speaker_recognition"
models_dir.mkdir(parents=True, exist_ok=True)

print(f"\n📥 Downloading speechbrain speaker recognition model...")
print(f"📂 Saving to: {models_dir}")
print(f"⏳ This will take a few minutes (~100MB)...\n")

# Download the model
classifier = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir=str(models_dir),
    run_opts={"device": "cpu"}
)

print("\n✅ Model downloaded successfully!")
print(f"📂 Model location: {models_dir}")
print(f"📦 Files downloaded:")

# List downloaded files
for file in models_dir.rglob("*"):
    if file.is_file():
        size_mb = file.stat().st_size / (1024 * 1024)
        print(f"   - {file.name} ({size_mb:.2f} MB)")

print("\n🎉 Ready to build Docker image with embedded model!")
print("   Run: docker build -t local-transcription-tool .")

