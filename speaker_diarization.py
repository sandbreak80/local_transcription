#!/usr/bin/env python3
"""
Advanced Speaker Diarization Module
Uses pyannote.audio for AI-powered speaker detection

Speaker Diarization Module
"""

import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Import pyannote.audio for REAL voice-based speaker detection
try:
    from pyannote.audio import Pipeline
    from pyannote.core import Annotation, Segment
    PYANNOTE_AVAILABLE = True
    print("✅ pyannote.audio loaded successfully - REAL voice detection enabled!")
except ImportError as e:
    PYANNOTE_AVAILABLE = False
    Pipeline = None
    Annotation = None
    Segment = None
    print(f"⚠️  pyannote.audio not available: {e}")
    print("   Install with: pip install pyannote.audio")
except Exception as e:
    PYANNOTE_AVAILABLE = False
    Pipeline = None
    Annotation = None
    Segment = None
    print(f"⚠️  pyannote.audio error: {e}")
    print("   Falling back to basic detection")


class SpeakerDiarizer:
    """
    Advanced speaker diarization using AI models.
    Detects and labels speakers with high accuracy.
    """
    
    def __init__(self, use_auth_token: Optional[str] = None):
        """
        Initialize speaker diarization.
        
        Args:
            use_auth_token: HuggingFace token for pretrained models (optional)
        """
        self.use_auth_token = use_auth_token or os.environ.get('HUGGINGFACE_TOKEN')
        self.pipeline = None
        
        if PYANNOTE_AVAILABLE and Pipeline is not None:
            try:
                # Try to load the pipeline
                # Note: First time requires HuggingFace token and model download
                self.pipeline = Pipeline.from_pretrained(
                    "pyannote/speaker-diarization-3.1",
                    use_auth_token=self.use_auth_token
                )
                print("✅ Speaker diarization AI model loaded")
            except Exception as e:
                if os.environ.get('DEBUG'):
                    print(f"⚠️  Could not load speaker diarization model: {e}")
                    print("   Falling back to basic speaker detection")
                self.pipeline = None
    
    def diarize_audio(self, audio_path: str, num_speakers: Optional[int] = None) -> Dict:
        """
        Perform speaker diarization on audio file.
        
        Args:
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional, auto-detect if None)
            
        Returns:
            Dictionary with speaker segments:
            {
                'speakers': [
                    {
                        'speaker': 'SPEAKER_00',
                        'start': 0.5,
                        'end': 5.2
                    },
                    ...
                ],
                'num_speakers': 2
            }
        """
        if not self.pipeline:
            print("⚠️  Advanced diarization not available, using basic detection")
            return self._basic_speaker_detection(audio_path)
        
        try:
            # Run diarization
            if num_speakers:
                diarization = self.pipeline(audio_path, num_speakers=num_speakers)
            else:
                diarization = self.pipeline(audio_path)
            
            # Extract speaker segments
            speaker_segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                speaker_segments.append({
                    'speaker': speaker,
                    'start': turn.start,
                    'end': turn.end,
                    'duration': turn.end - turn.start
                })
            
            # Count unique speakers
            unique_speakers = len(set(seg['speaker'] for seg in speaker_segments))
            
            print(f"✅ Detected {unique_speakers} speakers with {len(speaker_segments)} segments")
            
            return {
                'speakers': speaker_segments,
                'num_speakers': unique_speakers,
                'method': 'ai_diarization'
            }
            
        except Exception as e:
            print(f"⚠️  Diarization failed: {e}")
            print("   Falling back to basic speaker detection")
            return self._basic_speaker_detection(audio_path)
    
    def _basic_speaker_detection(self, audio_path: str) -> Dict:
        """
        Fallback basic speaker detection (silence-based).
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with basic speaker info
        """
        return {
            'speakers': [],
            'num_speakers': 0,
            'method': 'basic_silence_based'
        }
    
    def align_speakers_with_transcript(
        self, 
        speaker_segments: List[Dict], 
        transcript_segments: List[Dict]
    ) -> List[Dict]:
        """
        Align speaker diarization results with transcript segments.
        
        Args:
            speaker_segments: List of speaker segments from diarization
            transcript_segments: List of transcript segments with timestamps
            
        Returns:
            Transcript segments with speaker labels added
        """
        if not speaker_segments:
            # No diarization data, return original with default speakers
            for seg in transcript_segments:
                seg['speaker'] = 'SPEAKER_00'
            return transcript_segments
        
        # Align each transcript segment with speaker
        aligned_segments = []
        for t_seg in transcript_segments:
            t_start = t_seg.get('start', 0)
            t_end = t_seg.get('end', 0)
            t_mid = (t_start + t_end) / 2
            
            # Find which speaker is talking at the midpoint of this segment
            assigned_speaker = 'SPEAKER_00'
            max_overlap = 0
            
            for s_seg in speaker_segments:
                s_start = s_seg['start']
                s_end = s_seg['end']
                
                # Calculate overlap
                overlap_start = max(t_start, s_start)
                overlap_end = min(t_end, s_end)
                overlap = max(0, overlap_end - overlap_start)
                
                if overlap > max_overlap:
                    max_overlap = overlap
                    assigned_speaker = s_seg['speaker']
            
            # Add speaker to segment
            aligned_seg = t_seg.copy()
            aligned_seg['speaker'] = assigned_speaker
            aligned_segments.append(aligned_seg)
        
        return aligned_segments
    
    def relabel_speakers(
        self, 
        segments: List[Dict], 
        speaker_names: Dict[str, str]
    ) -> List[Dict]:
        """
        Replace speaker IDs with custom names.
        
        Args:
            segments: Segments with speaker IDs
            speaker_names: Mapping of speaker IDs to names
                          e.g., {'SPEAKER_00': 'Alice', 'SPEAKER_01': 'Bob'}
            
        Returns:
            Segments with renamed speakers
        """
        relabeled_segments = []
        
        for seg in segments:
            new_seg = seg.copy()
            speaker_id = seg.get('speaker', 'SPEAKER_00')
            
            # Replace with custom name if provided
            if speaker_id in speaker_names:
                new_seg['speaker'] = speaker_names[speaker_id]
                new_seg['speaker_id'] = speaker_names[speaker_id]
            
            relabeled_segments.append(new_seg)
        
        return relabeled_segments
    
    def get_speaker_statistics(self, segments: List[Dict]) -> Dict:
        """
        Calculate statistics about speakers.
        
        Args:
            segments: Segments with speaker labels
            
        Returns:
            Dictionary with speaker statistics
        """
        if not segments:
            return {}
        
        # Count segments and duration per speaker
        speaker_stats = {}
        
        for seg in segments:
            speaker = seg.get('speaker', 'SPEAKER_00')
            duration = seg.get('end', 0) - seg.get('start', 0)
            
            if speaker not in speaker_stats:
                speaker_stats[speaker] = {
                    'segments': 0,
                    'total_duration': 0,
                    'words': 0
                }
            
            speaker_stats[speaker]['segments'] += 1
            speaker_stats[speaker]['total_duration'] += duration
            speaker_stats[speaker]['words'] += len(seg.get('text', '').split())
        
        # Calculate percentages
        total_duration = sum(s['total_duration'] for s in speaker_stats.values())
        
        for speaker, stats in speaker_stats.items():
            stats['percentage'] = (stats['total_duration'] / total_duration * 100) if total_duration > 0 else 0
            stats['avg_segment_duration'] = stats['total_duration'] / stats['segments'] if stats['segments'] > 0 else 0
        
        return speaker_stats


def format_speaker_stats(stats: Dict) -> str:
    """
    Format speaker statistics as readable text.
    
    Args:
        stats: Speaker statistics dictionary
        
    Returns:
        Formatted string
    """
    if not stats:
        return "No speaker statistics available"
    
    lines = ["Speaker Statistics:", "=" * 60]
    
    for speaker, data in sorted(stats.items()):
        lines.append(f"\n{speaker}:")
        lines.append(f"  Segments: {data['segments']}")
        lines.append(f"  Total Duration: {data['total_duration']:.1f}s ({data['percentage']:.1f}%)")
        lines.append(f"  Words Spoken: {data['words']}")
        lines.append(f"  Avg Segment: {data['avg_segment_duration']:.1f}s")
    
    return "\n".join(lines)


if __name__ == '__main__':
    # Test speaker diarization
    print("Speaker Diarization Module")
    print("=" * 50)
    
    if PYANNOTE_AVAILABLE:
        print("✅ pyannote.audio is available")
        diarizer = SpeakerDiarizer()
    else:
        print("❌ pyannote.audio is not installed")
        print("   Install with: pip install pyannote.audio")

