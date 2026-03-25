#!/usr/bin/env python3
"""
Local Speaker Detection - NO external accounts required
Uses speechbrain for voice-based speaker recognition
Works completely offline after first model download

Local Speaker Detection Module
"""

import os
import numpy as np
import torch
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')

# Try to import speechbrain for speaker embeddings
SPEECHBRAIN_AVAILABLE = False
EncoderClassifier = None

try:
    from speechbrain.inference.speaker import EncoderClassifier
    SPEECHBRAIN_AVAILABLE = True
    print("✅ speechbrain loaded - Local voice detection enabled!")
except (ImportError, AttributeError, Exception) as e:
    # speechbrain has compatibility issues with torchaudio 2.9.0
    # Fall back to librosa-based audio feature clustering
    SPEECHBRAIN_AVAILABLE = False
    EncoderClassifier = None
    print(f"⚠️  speechbrain not available ({type(e).__name__})")
    print("   Using audio feature clustering for speaker detection")

import librosa
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score
from scipy.spatial.distance import cosine


class LocalSpeakerDetector:
    """
    Local speaker detection using voice embeddings.
    NO external accounts or API tokens required.
    Works completely offline.
    """
    
    def __init__(self):
        """Initialize the local speaker detector."""
        self.classifier = None
        
        if SPEECHBRAIN_AVAILABLE:
            try:
                # Load pre-trained speaker recognition model from embedded files
                # NO downloads needed - model is included in Docker image!
                model_dir = Path(__file__).parent / "models" / "speaker_recognition"
                
                if model_dir.exists():
                    self.classifier = EncoderClassifier.from_hparams(
                        source=str(model_dir),
                        savedir=str(model_dir),
                        run_opts={"device": "cpu"}
                    )
                    print("✅ Speaker recognition model loaded from embedded files (offline)")
                else:
                    # Fallback: download if embedded model not found
                    print("⚠️  Embedded model not found, downloading...")
                    self.classifier = EncoderClassifier.from_hparams(
                        source="speechbrain/spkrec-ecapa-voxceleb",
                        savedir="models/speaker_recognition",
                        run_opts={"device": "cpu"}
                    )
                    print("✅ Speaker recognition model downloaded and loaded")
            except Exception as e:
                print(f"⚠️  Could not load speaker model: {e}")
                print("   Using audio-based clustering fallback")
                self.classifier = None
    
    def extract_speaker_embeddings(self, audio_path: str, segments: List[Dict]) -> List[np.ndarray]:
        """
        Extract voice embeddings for each segment.
        
        Args:
            audio_path: Path to audio file
            segments: List of transcription segments with timing
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        # Load audio
        audio, sr = librosa.load(audio_path, sr=16000, mono=True)
        
        for segment in segments:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            
            # Extract audio segment
            start_sample = int(start_time * sr)
            end_sample = int(end_time * sr)
            segment_audio = audio[start_sample:end_sample]
            
            if len(segment_audio) < sr * 0.5:  # Skip segments shorter than 0.5s
                embeddings.append(None)
                continue
            
            # Extract embedding
            if self.classifier and SPEECHBRAIN_AVAILABLE:
                # Use speechbrain for voice embeddings
                try:
                    with torch.no_grad():
                        embedding = self.classifier.encode_batch(
                            torch.FloatTensor(segment_audio).unsqueeze(0)
                        )
                        embeddings.append(embedding.squeeze().numpy())
                except Exception as e:
                    print(f"⚠️  Embedding extraction failed: {e}")
                    embeddings.append(self._extract_audio_features(segment_audio, sr))
            else:
                # Fallback: Use audio features
                embeddings.append(self._extract_audio_features(segment_audio, sr))
        
        return embeddings
    
    def _extract_audio_features(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """
        Extract audio features as a fallback embedding.
        Uses MFCCs and spectral features.
        """
        # Extract MFCCs
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        mfcc_mean = np.mean(mfccs, axis=1)
        
        # Extract spectral features
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio, sr=sr))
        spectral_rolloff = np.mean(librosa.feature.spectral_rolloff(y=audio, sr=sr))
        zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(audio))
        
        # Combine features
        features = np.concatenate([
            mfcc_mean,
            [spectral_centroid, spectral_rolloff, zero_crossing_rate]
        ])
        
        return features
    
    def cluster_speakers(self, embeddings: List[np.ndarray], num_speakers: Optional[int] = None) -> List[int]:
        """
        Cluster embeddings to identify speakers.
        
        Args:
            embeddings: List of embedding vectors
            num_speakers: Expected number of speakers (optional)
            
        Returns:
            List of speaker IDs (one per embedding)
        """
        # Filter out None embeddings
        valid_embeddings = []
        valid_indices = []
        
        for i, emb in enumerate(embeddings):
            if emb is not None:
                valid_embeddings.append(emb)
                valid_indices.append(i)
        
        if not valid_embeddings:
            return [0] * len(embeddings)

        # Need at least 2 embeddings to cluster
        if len(valid_embeddings) == 1:
            return [0] * len(embeddings)

        X = np.array(valid_embeddings)

        if num_speakers is None:
            num_speakers = self._auto_detect_speakers(X)

        num_speakers = max(1, min(num_speakers, len(valid_embeddings)))

        if num_speakers == 1:
            result = [0] * len(embeddings)
            return result

        clustering = AgglomerativeClustering(
            n_clusters=num_speakers,
            metric='cosine',
            linkage='average'
        )
        labels = clustering.fit_predict(X)

        # Map back to full list — use -1 for None embeddings (too short)
        result = [-1] * len(embeddings)
        for i, idx in enumerate(valid_indices):
            result[idx] = int(labels[i])

        # Assign short segments to nearest neighbor speaker
        for i, label in enumerate(result):
            if label == -1:
                result[i] = self._nearest_speaker(i, result)

        return result

    def _auto_detect_speakers(self, X: np.ndarray) -> int:
        """Auto-detect number of speakers using silhouette score."""
        n_samples = len(X)
        max_k = min(n_samples - 1, 10)  # Max 10 speakers

        if max_k < 2:
            return 1

        best_k = 2
        best_score = -1

        for k in range(2, max_k + 1):
            try:
                clustering = AgglomerativeClustering(
                    n_clusters=k, metric='cosine', linkage='average')
                labels = clustering.fit_predict(X)

                # Skip if all in one cluster
                if len(set(labels)) < 2:
                    continue

                score = silhouette_score(X, labels, metric='cosine')
                print(f"  k={k}: silhouette={score:.3f}")

                if score > best_score:
                    best_score = score
                    best_k = k
            except Exception:
                continue

        print(f"  Auto-detected {best_k} speakers (silhouette={best_score:.3f})")
        return best_k

    def _nearest_speaker(self, idx: int, labels: list) -> int:
        """Assign a short segment to the nearest valid speaker by proximity."""
        # Look outward from idx for the nearest labeled segment
        for dist in range(1, len(labels)):
            if idx - dist >= 0 and labels[idx - dist] >= 0:
                return labels[idx - dist]
            if idx + dist < len(labels) and labels[idx + dist] >= 0:
                return labels[idx + dist]
        return 0
    
    def diarize(self, audio_path: str, segments: List[Dict], num_speakers: Optional[int] = None) -> List[Dict]:
        """
        Perform complete speaker diarization.
        
        Args:
            audio_path: Path to audio file
            segments: Transcription segments
            num_speakers: Expected number of speakers (optional)
            
        Returns:
            Segments with speaker_id added
        """
        print("🎤 Analyzing voices for speaker detection...")
        
        # Extract embeddings
        embeddings = self.extract_speaker_embeddings(audio_path, segments)
        
        # Cluster speakers
        speaker_ids = self.cluster_speakers(embeddings, num_speakers)
        
        # Add speaker IDs to segments
        for segment, speaker_id in zip(segments, speaker_ids):
            segment['speaker_id'] = f"SPEAKER_{speaker_id:02d}"
        
        # Count speakers
        unique_speakers = len(set(speaker_ids))
        print(f"✅ Detected {unique_speakers} speaker(s)")
        
        return segments


def format_speaker_stats(segments: List[Dict]) -> str:
    """
    Format speaker statistics.
    
    Args:
        segments: Segments with speaker_id
        
    Returns:
        Formatted statistics string
    """
    from collections import defaultdict
    
    speaker_stats = defaultdict(lambda: {'count': 0, 'duration': 0.0})
    
    for segment in segments:
        speaker = segment.get('speaker_id', 'UNKNOWN')
        duration = segment.get('end', 0) - segment.get('start', 0)
        
        speaker_stats[speaker]['count'] += 1
        speaker_stats[speaker]['duration'] += duration
    
    output = "\n📊 Speaker Statistics:\n"
    output += "-" * 50 + "\n"
    
    for speaker in sorted(speaker_stats.keys()):
        stats = speaker_stats[speaker]
        minutes = int(stats['duration'] // 60)
        seconds = int(stats['duration'] % 60)
        output += f"{speaker}: {stats['count']} segments, {minutes}m {seconds}s total\n"
    
    return output

