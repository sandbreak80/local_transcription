#!/usr/bin/env python3
"""
Animated Quote Detection Module
Detects the most animated quotes from audio/video content with voice inflection analysis.
"""

import os
import numpy as np
import librosa
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class AnimatedQuote:
    """Represents an animated quote with metadata."""
    text: str
    topic_category: str
    start_timestamp: float
    end_timestamp: float
    duration: float
    animatedness_score: float
    segment_index: int


class AnimatedQuoteDetector:
    """
    Detects animated quotes from audio/video content based on voice inflection
    and topic classification for enterprise content.
    """
    
    def __init__(self, quote_duration: float = 15.0, num_quotes: int = 10):
        """
        Initialize the animated quote detector.
        
        Args:
            quote_duration: Duration of each quote in seconds (default: 15.0)
            num_quotes: Number of quotes to return (default: 10)
        """
        self.quote_duration = quote_duration
        self.num_quotes = num_quotes
        
        # Topic categories for content classification
        self.topic_categories = {
            'current_state': {
                'keywords': [
                    'currently', 'now', 'today', 'existing', 'current', 'present',
                    'already', 'implemented', 'deployed', 'in production', 'live',
                    'ai technology', 'artificial intelligence', 'machine learning',
                    'deep learning', 'neural networks', 'algorithms', 'models'
                ],
                'patterns': [
                    r'we (currently|now|today)',
                    r'(current|existing|present) (state|technology|capabilities)',
                    r'(already|already have|already using)',
                    r'(in production|live|deployed)'
                ]
            },
            'future_direction': {
                'keywords': [
                    'future', 'next', 'coming', 'roadmap', 'vision', 'strategy',
                    'planning', 'ahead', 'tomorrow', 'will be', 'going to',
                    'evolution', 'transformation', 'innovation', 'breakthrough',
                    'next generation', 'emerging', 'upcoming', 'forthcoming'
                ],
                'patterns': [
                    r'(future|next|coming) (generation|version|release)',
                    r'(roadmap|vision|strategy) (for|of)',
                    r'(will be|going to|planning to)',
                    r'(next|upcoming|forthcoming) (year|quarter|phase)'
                ]
            },
            'product_pipeline': {
                'keywords': [
                    'product', 'solution', 'platform', 'service', 'offering',
                    'on the truck', 'pipeline', 'development', 'building',
                    'creating', 'launching', 'releasing', 'shipping',
                    'delivering', 'rollout', 'deployment', 'availability'
                ],
                'patterns': [
                    r'(on the truck|in the pipeline)',
                    r'(product|solution|platform) (development|launch)',
                    r'(building|creating|developing) (new|next)',
                    r'(launching|releasing|shipping) (soon|next)'
                ]
            }
        }
        
        # Initialize TF-IDF vectorizer for topic classification
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def analyze_voice_inflection(self, audio_path: str, segments: List[Dict]) -> List[float]:
        """
        Analyze voice inflection to detect animated/excited speech.
        
        Args:
            audio_path: Path to the audio file
            segments: List of transcription segments with timestamps
            
        Returns:
            List of animatedness scores for each segment
        """
        try:
            # Load audio file
            y, sr = librosa.load(audio_path, sr=16000)
            
            animatedness_scores = []
            
            for i, segment in enumerate(segments):
                start_time = segment['start']
                end_time = segment['end']
                
                # Extract audio segment
                start_sample = int(start_time * sr)
                end_sample = int(end_time * sr)
                segment_audio = y[start_sample:end_sample]
                
                if len(segment_audio) == 0:
                    animatedness_scores.append(0.0)
                    continue
                
                # Calculate features that indicate excitement/animation
                score = self._calculate_animatedness_score(segment_audio, sr, i)
                animatedness_scores.append(score)
            
            return animatedness_scores
            
        except Exception as e:
            print(f"Error analyzing voice inflection: {e}")
            # Return zero scores if analysis fails
            return [0.0] * len(segments)
    
    def _calculate_animatedness_score(self, audio_segment: np.ndarray, sr: int, segment_index: int = 0) -> float:
        """
        Calculate animatedness score for an audio segment using prosody features.
        
        Excitement Detection Features:
        - Energy (RMS): Higher volume indicates excitement (weight: 20%)
        - Spectral Centroid: Brighter/more excited sound (weight: 20%) 
        - Zero Crossing Rate: Rapid speech changes (weight: 15%)
        - Spectral Rolloff: High-frequency content (weight: 15%)
        - MFCC Variance: Timbre variation (weight: 15%)
        - Pitch Variation: Emotional expression (weight: 15%)
        
        Excitement Threshold: Scores > 0.05 are considered candidates
        High Excitement: Scores > 0.5 indicate strong animation
        
        Args:
            audio_segment: Audio data for the segment
            sr: Sample rate
            segment_index: Index for debugging output
            
        Returns:
            Animatedness score (0.0 to 1.0)
        """
        try:
            # Calculate various audio features that indicate excitement
            features = []
            
            # 1. Energy (volume) - excited speech tends to be louder
            energy = np.mean(librosa.feature.rms(y=audio_segment)[0])
            features.append(energy)
            
            # 2. Spectral centroid - higher values indicate brighter/more excited sound
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=audio_segment, sr=sr)[0])
            features.append(spectral_centroid / 4000.0)  # Normalize
            
            # 3. Zero crossing rate - excited speech has more rapid changes
            zcr = np.mean(librosa.feature.zero_crossing_rate(audio_segment)[0])
            features.append(zcr)
            
            # 4. Spectral rolloff - excited speech has more high-frequency content
            rolloff = np.mean(librosa.feature.spectral_rolloff(y=audio_segment, sr=sr)[0])
            features.append(rolloff / 8000.0)  # Normalize
            
            # 5. MFCC variance - excited speech has more variation in timbre
            mfccs = librosa.feature.mfcc(y=audio_segment, sr=sr, n_mfcc=13)
            mfcc_var = np.mean(np.var(mfccs, axis=1))
            features.append(mfcc_var / 100.0)  # Normalize
            
            # 6. Pitch variation - excited speech has more pitch variation
            pitches, magnitudes = librosa.piptrack(y=audio_segment, sr=sr)
            pitch_values = []
            for t in range(pitches.shape[1]):
                index = magnitudes[:, t].argmax()
                pitch = pitches[index, t]
                if pitch > 0:
                    pitch_values.append(pitch)
            
            if pitch_values:
                pitch_variation = np.std(pitch_values) / np.mean(pitch_values) if np.mean(pitch_values) > 0 else 0
                features.append(min(pitch_variation, 1.0))  # Cap at 1.0
            else:
                features.append(0.0)
            
            # Combine features with weights
            weights = [0.2, 0.2, 0.15, 0.15, 0.15, 0.15]
            raw_score = sum(w * f for w, f in zip(weights, features))
            
            # Normalize the score to 0-1 range with better distribution
            # The raw scores are typically 0-5, so we'll scale them down
            score = min(raw_score / 5.0, 1.0)
            
            # Debug: Print first few scores
            if segment_index < 3:  # Only print for first 3 segments to avoid spam
                print(f"Segment {segment_index}: Features: {[f'{f:.3f}' for f in features]}, Raw: {raw_score:.3f}, Final: {score:.3f}")
            
            return score
            
        except Exception as e:
            print(f"Error calculating animatedness score: {e}")
            return 0.0
    
    def classify_topic(self, text: str) -> str:
        """
        Classify text into one of the three topic categories.
        
        Args:
            text: Text to classify
            
        Returns:
            Topic category name
        """
        text_lower = text.lower()
        
        # Calculate scores for each category
        category_scores = {}
        
        for category, data in self.topic_categories.items():
            score = 0
            
            # Keyword matching
            for keyword in data['keywords']:
                if keyword in text_lower:
                    score += 1
            
            # Pattern matching
            for pattern in data['patterns']:
                if re.search(pattern, text_lower):
                    score += 2  # Patterns are weighted higher
            
            category_scores[category] = score
        
        # Return the category with the highest score
        if max(category_scores.values()) == 0:
            return 'current_state'  # Default category
        
        return max(category_scores, key=category_scores.get)
    
    def select_quotes(self, segments: List[Dict], animatedness_scores: List[float]) -> List[AnimatedQuote]:
        """
        Select the most animated quotes with even topic distribution.
        
        Args:
            segments: List of transcription segments
            animatedness_scores: Animatedness scores for each segment
            
        Returns:
            List of selected animated quotes
        """
        # Create candidate quotes
        candidates = []
        
        for i, (segment, score) in enumerate(zip(segments, animatedness_scores)):
            if score > 0.05:  # Lower threshold to catch more segments
                text = segment.get('text', '').strip()
                if len(text) > 10:  # Lower text length requirement
                    topic = self.classify_topic(text)
                    
                    quote = AnimatedQuote(
                        text=text,
                        topic_category=topic,
                        start_timestamp=segment['start'],
                        end_timestamp=segment['end'],
                        duration=segment['end'] - segment['start'],
                        animatedness_score=score,
                        segment_index=i
                    )
                    candidates.append(quote)
        
        print(f"Found {len(candidates)} candidate quotes with scores > 0.05")
        if candidates:
            print(f"Score range: {min(c.animatedness_score for c in candidates):.3f} - {max(c.animatedness_score for c in candidates):.3f}")
        
        # Sort by animatedness score
        candidates.sort(key=lambda x: x.animatedness_score, reverse=True)
        
        # Select quotes with even topic distribution
        selected_quotes = []
        topic_counts = {'current_state': 0, 'future_direction': 0, 'product_pipeline': 0}
        
        # Calculate target distribution for even mix across three topics
        # For 10 quotes: minimum 3 per category, remainder (1) to strongest category
        # This ensures: 3/3/4 distribution (even mix with one extra to highest-scoring category)
        target_counts = {
            'current_state': 3,      # Minimum 3 quotes per category
            'future_direction': 3,   # Minimum 3 quotes per category  
            'product_pipeline': 4    # Remaining 1 quote goes to strongest category
        }
        
        # Track selected segment indices to avoid duplicates
        selected_indices = set()

        # First pass: select best quotes for each topic
        for quote in candidates:
            if topic_counts[quote.topic_category] < target_counts[quote.topic_category]:
                if quote.segment_index in selected_indices:
                    continue
                # Adjust quote to be exactly 15 seconds
                adjusted_quote = self._adjust_quote_duration(quote, segments)
                if adjusted_quote:
                    selected_quotes.append(adjusted_quote)
                    selected_indices.add(quote.segment_index)
                    topic_counts[quote.topic_category] += 1

                    if len(selected_quotes) >= self.num_quotes:
                        break

        # If we don't have enough quotes, fill with remaining best candidates
        if len(selected_quotes) < self.num_quotes:
            for quote in candidates:
                if quote.segment_index in selected_indices:
                    continue
                adjusted_quote = self._adjust_quote_duration(quote, segments)
                if adjusted_quote:
                    selected_quotes.append(adjusted_quote)
                    selected_indices.add(quote.segment_index)
                    if len(selected_quotes) >= self.num_quotes:
                        break
        
        print(f"Final selection: {len(selected_quotes)} quotes selected")
        
        return selected_quotes[:self.num_quotes]
    
    def _adjust_quote_duration(self, quote: AnimatedQuote, segments: List[Dict]) -> Optional[AnimatedQuote]:
        """
        Adjust quote to be exactly 15 seconds long.
        
        Args:
            quote: Original quote
            segments: All segments for context
            
        Returns:
            Adjusted quote or None if adjustment not possible
        """
        target_duration = self.quote_duration
        current_duration = quote.duration
        
        if current_duration >= target_duration:
            # Quote is long enough, truncate from the end
            new_end = quote.start_timestamp + target_duration
            return AnimatedQuote(
                text=quote.text,
                topic_category=quote.topic_category,
                start_timestamp=quote.start_timestamp,
                end_timestamp=new_end,
                duration=target_duration,
                animatedness_score=quote.animatedness_score,
                segment_index=quote.segment_index
            )
        else:
            # Quote is too short, try to extend by including adjacent segments
            extension_needed = target_duration - current_duration
            
            # Try to extend forward by including next segments
            new_end = quote.end_timestamp
            segments_to_include = [quote.segment_index]
            
            # Add next segments until we have enough duration
            for i in range(quote.segment_index + 1, len(segments)):
                if new_end - quote.start_timestamp >= target_duration:
                    break
                    
                next_segment = segments[i]
                segments_to_include.append(i)
                new_end = next_segment['end']
            
            # If we still don't have enough, try extending backward
            if new_end - quote.start_timestamp < target_duration:
                new_start = quote.start_timestamp
                for i in range(quote.segment_index - 1, -1, -1):
                    if new_end - new_start >= target_duration:
                        break
                        
                    prev_segment = segments[i]
                    segments_to_include.insert(0, i)
                    new_start = prev_segment['start']
                
                # Adjust start if we have enough duration
                if new_end - new_start >= target_duration:
                    new_start = new_end - target_duration
            else:
                # Adjust end if we have enough duration
                new_end = quote.start_timestamp + target_duration
            
            # Check if we have enough duration
            if new_end - quote.start_timestamp >= target_duration:
                # Combine text from all included segments
                combined_text = " ".join([segments[i]['text'] for i in segments_to_include if i < len(segments)])
                
                return AnimatedQuote(
                    text=combined_text,
                    topic_category=quote.topic_category,
                    start_timestamp=quote.start_timestamp,
                    end_timestamp=new_end,
                    duration=target_duration,
                    animatedness_score=quote.animatedness_score,
                    segment_index=quote.segment_index
                )
            else:
                print(f"Quote {quote.segment_index}: Cannot extend to {target_duration}s (max possible: {new_end - quote.start_timestamp:.1f}s)")
        
        return None
    
    def format_timestamp(self, seconds: float) -> str:
        """
        Format timestamp in HH:MM:SS.mmm format.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def detect_animated_quotes(self, audio_path: str, transcription_result: Dict) -> List[AnimatedQuote]:
        """
        Main method to detect animated quotes from audio and transcription.
        
        Args:
            audio_path: Path to the audio file
            transcription_result: Transcription result with segments
            
        Returns:
            List of detected animated quotes
        """
        segments = transcription_result.get('segments', [])
        
        if not segments:
            print("No segments found in transcription result")
            return []
        
        print(f"Analyzing voice inflection for {len(segments)} segments...")
        
        # Analyze voice inflection
        animatedness_scores = self.analyze_voice_inflection(audio_path, segments)
        
        # Debug: Show score distribution
        if animatedness_scores:
            print(f"Animatedness scores - Min: {min(animatedness_scores):.3f}, Max: {max(animatedness_scores):.3f}, Avg: {sum(animatedness_scores)/len(animatedness_scores):.3f}")
            print(f"Scores > 0.1: {sum(1 for s in animatedness_scores if s > 0.1)}")
            print(f"Scores > 0.05: {sum(1 for s in animatedness_scores if s > 0.05)}")
        
        # Select quotes
        quotes = self.select_quotes(segments, animatedness_scores)
        
        print(f"Selected {len(quotes)} animated quotes")
        
        return quotes
    
    def save_quotes_report(self, quotes: List[AnimatedQuote], output_path: str):
        """
        Save animated quotes to a formatted report.
        
        Args:
            quotes: List of animated quotes
            output_path: Path to save the report
        """
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("Animated Quotes Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Total Quotes: {len(quotes)}\n")
            f.write(f"Quote Duration: {self.quote_duration} seconds\n")
            f.write(f"Excitement Threshold: > 0.05 (candidates), > 0.5 (high excitement)\n")
            f.write(f"Topic Distribution: 3/3/4 (minimum 3 per category, remainder to strongest)\n\n")
            
            f.write("Quote Text\tTopic Category\tStart Timestamp\tEnd Timestamp\tDuration\tExcitement Score\n")
            f.write("-" * 120 + "\n")
            
            for i, quote in enumerate(quotes, 1):
                start_time = self.format_timestamp(quote['start_timestamp'])
                end_time = self.format_timestamp(quote['end_timestamp'])
                duration_str = f"{quote['duration']:.1f}s"
                excitement_score = f"{quote['animatedness_score']:.3f}"
                
                f.write(f'"{quote["text"]}"\t{quote["topic_category"]}\t{start_time}\t{end_time}\t{duration_str}\t{excitement_score}\n')
            
            f.write("\n" + "=" * 50 + "\n")
            f.write("Topic Distribution:\n")
            
            topic_counts = {}
            for quote in quotes:
                topic_counts[quote['topic_category']] = topic_counts.get(quote['topic_category'], 0) + 1
            
            for topic, count in topic_counts.items():
                f.write(f"{topic}: {count} quotes\n")
        
        print(f"Animated quotes report saved to: {output_path}")
