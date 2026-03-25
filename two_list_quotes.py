#!/usr/bin/env python3
"""
Two-List Quote Detection Module
Implements the two-list feature: List 1 (arbitrary quotes) and List 2 (animated quotes with topic mix).
"""

import os
import numpy as np
import librosa
import re
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass
from pathlib import Path
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Quote:
    """Represents a quote with metadata."""
    text: str
    start_timestamp: float
    end_timestamp: float
    duration: float
    speaker_id: Optional[str] = None
    segment_index: int = 0


@dataclass
class AnimatedQuote(Quote):
    """Represents an animated quote with additional metadata."""
    topic_category: str = ""
    excitement_score: float = 0.0
    classification_confidence: float = 0.0


class TwoListQuoteDetector:
    """
    Detects two distinct lists of quotes:
    1. List 1: Ten arbitrary 15-second quotes (sentence-aligned)
    2. List 2: Twelve most animated quotes with topic mix (30% each category)
    """
    
    def __init__(self, list1_duration: float = 15.0, list1_count: int = 10, 
                 list2_max_duration: float = 15.0, list2_count: int = 12):
        """
        Initialize the two-list quote detector.
        
        Args:
            list1_duration: Duration of List 1 quotes in seconds (default: 15.0)
            list1_count: Number of quotes in List 1 (default: 10)
            list2_max_duration: Maximum duration of List 2 quotes in seconds (default: 15.0)
            list2_count: Number of quotes in List 2 (default: 12)
        """
        self.list1_duration = list1_duration
        self.list1_count = list1_count
        self.list2_max_duration = list2_max_duration
        self.list2_count = list2_count
        
        # Updated topic categories to match new spec
        self.topic_categories = {
            'current_state': {
                'keywords': [
                    'currently', 'now', 'today', 'existing', 'current', 'present',
                    'already', 'implemented', 'deployed', 'in production', 'live',
                    'ai technology', 'artificial intelligence', 'machine learning',
                    'deep learning', 'neural networks', 'algorithms', 'models',
                    'we currently', 'we have', 'we are', 'our current'
                ],
                'patterns': [
                    r'we (currently|now|today)',
                    r'(current|existing|present) (state|technology|capabilities)',
                    r'(already|already have|already using)',
                    r'(in production|live|deployed)',
                    r'(company|organization) (is|has|currently)'
                ]
            },
            'future_direction': {
                'keywords': [
                    'future', 'next', 'coming', 'roadmap', 'vision', 'strategy',
                    'planning', 'ahead', 'tomorrow', 'will be', 'going to',
                    'evolution', 'transformation', 'innovation', 'breakthrough',
                    'next generation', 'emerging', 'upcoming', 'forthcoming',
                    'we are going', 'we will', 'we will', 'the future of'
                ],
                'patterns': [
                    r'(future|next|coming) (generation|version|release)',
                    r'(roadmap|vision|strategy) (for|of)',
                    r'(will be|going to|planning to)',
                    r'(next|upcoming|forthcoming) (year|quarter|phase)',
                    r'(company|organization) (will|is going to|plans to)'
                ]
            },
            'products': {
                'keywords': [
                    'product', 'solution', 'platform', 'service', 'offering',
                    'on the truck', 'pipeline', 'development', 'building',
                    'creating', 'launching', 'releasing', 'shipping',
                    'delivering', 'rollout', 'deployment', 'availability',
                    'our product', 'our product', 'our solution', 'our solution'
                ],
                'patterns': [
                    r'(on the truck|in the pipeline)',
                    r'(product|solution|platform) (development|launch)',
                    r'(building|creating|developing) (new|next)',
                    r'(launching|releasing|shipping) (soon|next)',
                    r'(our|the) (product|solution|platform)'
                ]
            }
        }
        
        # Initialize TF-IDF vectorizer for topic classification
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
    
    def detect_two_lists(self, audio_path: str, transcription_result: Dict) -> Dict:
        """
        Main method to detect both lists of quotes.
        
        Args:
            audio_path: Path to the audio file
            transcription_result: Transcription result with segments
            
        Returns:
            Dictionary with both lists of quotes
        """
        segments = transcription_result.get('segments', [])
        
        if not segments:
            print("No segments found in transcription result")
            return {'list1_arbitrary_15s_quotes': [], 'list2_animated_quotes': []}
        
        print(f"Processing {len(segments)} segments for two-list quote detection...")
        
        # Detect speaker changes and assign speaker IDs
        segments_with_speakers = self._detect_speakers(segments)
        
        # Generate List 1: Arbitrary 15-second quotes
        print("Generating List 1: Arbitrary 15-second quotes...")
        list1_quotes = self._generate_list1_arbitrary_quotes(segments_with_speakers)
        
        # Generate List 2: Animated quotes with topic mix
        print("Generating List 2: Animated quotes with topic mix...")
        list2_quotes = self._generate_list2_animated_quotes(audio_path, segments_with_speakers, list1_quotes)
        
        # Convert to output format
        return {
            'list1_arbitrary_15s_quotes': [self._quote_to_dict(q) for q in list1_quotes],
            'list2_animated_quotes': [self._animated_quote_to_dict(q) for q in list2_quotes]
        }
    
    def _detect_speakers(self, segments: List[Dict]) -> List[Dict]:
        """
        Detect speaker changes and assign speaker IDs.
        
        Args:
            segments: List of transcription segments
            
        Returns:
            Segments with speaker IDs added
        """
        segments_with_speakers = []
        current_speaker = "S1"
        speaker_count = 1
        last_end_time = 0
        
        for i, segment in enumerate(segments):
            start_time = segment.get('start', 0)
            
            # Check for speaker change (gap > 2 seconds indicates potential speaker change)
            if start_time - last_end_time > 2.0 and i > 0:
                speaker_count += 1
                current_speaker = f"S{speaker_count}"
            
            segment_with_speaker = segment.copy()
            segment_with_speaker['speaker_id'] = current_speaker
            segments_with_speakers.append(segment_with_speaker)
            
            last_end_time = segment.get('end', 0)
        
        return segments_with_speakers
    
    def _generate_list1_arbitrary_quotes(self, segments: List[Dict]) -> List[Quote]:
        """
        Generate List 1: Ten arbitrary 15-second quotes (sentence-aligned).
        
        Args:
            segments: Segments with speaker IDs
            
        Returns:
            List of arbitrary quotes
        """
        quotes = []
        used_timestamps = set()
        
        # Adjust list1_count based on video duration to leave room for List 2
        total_duration = max(seg.get('end', 0) for seg in segments) if segments else 0
        max_list1_duration = total_duration * 0.4  # Use only 40% of video for List 1
        adjusted_list1_count = min(self.list1_count, int(max_list1_duration / self.list1_duration))
        
        print(f"Video duration: {total_duration:.1f}s, using {adjusted_list1_count} quotes for List 1")
        
        # Create 15-second quotes by combining adjacent segments
        for i in range(adjusted_list1_count):
            target_start = (i * total_duration) / adjusted_list1_count
            
            # Find the best starting point near target time
            best_start_segment = None
            best_distance = float('inf')
            
            for j, segment in enumerate(segments):
                start_time = segment.get('start', 0)
                
                # Check if this would overlap with used timestamps
                if self._has_overlap(start_time, start_time + self.list1_duration, used_timestamps):
                    continue
                
                # Find closest segment to target time
                if abs(start_time - target_start) < best_distance:
                    best_distance = abs(start_time - target_start)
                    best_start_segment = j
            
            if best_start_segment is not None:
                # Build 15-second quote starting from this segment
                quote_segments = self._build_15_second_quote(segments, best_start_segment, self.list1_duration)
                
                if quote_segments:
                    # Combine text from all segments
                    combined_text = ' '.join([seg.get('text', '').strip() for seg in quote_segments])
                    combined_text = ' '.join(combined_text.split())  # Clean up whitespace
                    
                    # Get timing from first and last segments
                    start_time = quote_segments[0]['start']
                    end_time = quote_segments[-1]['end']
                    speaker_id = quote_segments[0].get('speaker_id', 'S1')
                    
                    # Ensure exactly 15 seconds
                    if end_time - start_time < self.list1_duration:
                        end_time = start_time + self.list1_duration
                    
                    quote = Quote(
                        text=combined_text,
                        start_timestamp=start_time,
                        end_timestamp=end_time,
                        duration=self.list1_duration,
                        speaker_id=speaker_id,
                        segment_index=i
                    )
                    quotes.append(quote)
                    
                    # Mark timestamps as used
                    used_timestamps.add((quote.start_timestamp, quote.end_timestamp))
        
        return quotes[:adjusted_list1_count]
    
    def _generate_list2_animated_quotes(self, audio_path: str, segments: List[Dict], 
                                      list1_quotes: List[Quote]) -> List[AnimatedQuote]:
        """
        Generate List 2: Twelve most animated quotes with topic mix.
        
        Args:
            audio_path: Path to the audio file
            segments: Segments with speaker IDs
            list1_quotes: List 1 quotes to avoid overlap
            
        Returns:
            List of animated quotes
        """
        # Analyze voice inflection
        print("Analyzing voice inflection for animated quotes...")
        animatedness_scores = self._analyze_voice_inflection(audio_path, segments)
        
        # Create candidate quotes
        candidates = []
        list1_timestamps = {(q.start_timestamp, q.end_timestamp) for q in list1_quotes}
        
        print(f"Analyzing {len(segments)} segments for List 2 candidates...")
        print(f"Animatedness scores range: {min(animatedness_scores):.3f} - {max(animatedness_scores):.3f}")
        
        # Create 15-second quotes for List 2 by combining segments
        for i, (segment, score) in enumerate(zip(segments, animatedness_scores)):
            if score > 0.01:  # Lower threshold to get more candidates
                # Build a 15-second quote starting from this segment
                quote_segments = self._build_15_second_quote(segments, i, self.list2_max_duration)
                
                if quote_segments:
                    # Combine text from all segments
                    combined_text = ' '.join([seg.get('text', '').strip() for seg in quote_segments])
                    combined_text = ' '.join(combined_text.split())  # Clean up whitespace
                    
                    if len(combined_text) > 20:  # Ensure meaningful content
                        # Get timing from first and last segments
                        start_time = quote_segments[0]['start']
                        end_time = quote_segments[-1]['end']
                        speaker_id = quote_segments[0].get('speaker_id', 'S1')
                        
                        # Ensure we don't exceed max duration
                        if end_time - start_time > self.list2_max_duration:
                            end_time = start_time + self.list2_max_duration
                        
                        # Check for overlap with List 1
                        has_overlap = self._has_overlap(start_time, end_time, list1_timestamps)
                        
                        if not has_overlap:
                            # Classify topic based on combined text
                            topic = self.classify_topic(combined_text)
                            confidence = self._calculate_classification_confidence(combined_text, topic)
                            
                            # Use the highest excitement score from the segments
                            max_score = max(animatedness_scores[j] for j in range(i, i + len(quote_segments)))
                            
                            quote = AnimatedQuote(
                                text=combined_text,
                                start_timestamp=start_time,
                                end_timestamp=end_time,
                                duration=end_time - start_time,
                                speaker_id=speaker_id,
                                segment_index=i,
                                topic_category=topic,
                                excitement_score=max_score,
                                classification_confidence=confidence
                            )
                            candidates.append(quote)
                        else:
                            print(f"Quote starting at segment {i} (score {score:.3f}) overlaps with List 1")
                    else:
                        print(f"Quote starting at segment {i} (score {score:.3f}) text too short: '{combined_text[:50]}...'")
            else:
                if i < 5:  # Only print first few for debugging
                    print(f"Segment {i} score too low: {score:.3f}")
        
        # Sort by animatedness score
        candidates.sort(key=lambda x: x.excitement_score, reverse=True)
        
        print(f"Found {len(candidates)} candidate quotes for List 2")
        if candidates:
            print(f"Top 5 excitement scores: {[c.excitement_score for c in candidates[:5]]}")
            print(f"Topic distribution: {[c.topic_category for c in candidates[:10]]}")
        
        # Select quotes with topic mix (30% each category)
        selected_quotes = self._select_with_topic_mix(candidates)
        
        print(f"Selected {len(selected_quotes)} quotes for List 2")
        
        return selected_quotes[:self.list2_count]
    
    def _create_sentence_aligned_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Create sentence-aligned segments for better quote boundaries.
        
        Args:
            segments: Original segments
            
        Returns:
            Sentence-aligned segments
        """
        sentence_segments = []
        
        for segment in segments:
            text = segment.get('text', '').strip()
            sentences = self._split_into_sentences(text)
            
            if len(sentences) == 1:
                sentence_segments.append(segment)
            else:
                # Split into individual sentences
                start_time = segment['start']
                end_time = segment['end']
                duration = end_time - start_time
                
                for i, sentence in enumerate(sentences):
                    if not sentence.strip():
                        continue
                    
                    sentence_start = start_time + (i * duration / len(sentences))
                    sentence_end = start_time + ((i + 1) * duration / len(sentences))
                    
                    sentence_segment = segment.copy()
                    sentence_segment.update({
                        'text': sentence,
                        'start': sentence_start,
                        'end': sentence_end
                    })
                    sentence_segments.append(sentence_segment)
        
        return sentence_segments
    
    def _split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using simple heuristics.
        
        Args:
            text: Text to split
            
        Returns:
            List of sentences
        """
        import re
        
        # Split on sentence endings, but be careful with abbreviations
        sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text)
        
        # Clean up and filter empty sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 3:  # Filter out very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def _has_overlap(self, start: float, end: float, used_timestamps: Set[Tuple[float, float]]) -> bool:
        """
        Check if a time range overlaps with any used timestamps.
        
        Args:
            start: Start time
            end: End time
            used_timestamps: Set of used timestamp ranges
            
        Returns:
            True if there's an overlap
        """
        for used_start, used_end in used_timestamps:
            if not (end <= used_start or start >= used_end):
                return True
        return False
    
    def _extend_text_to_duration(self, text: str, target_duration: float) -> str:
        """
        Extend text to fill target duration.
        
        Args:
            text: Original text
            target_duration: Target duration in seconds
            
        Returns:
            Extended text
        """
        # For now, just return the original text
        # In a more sophisticated implementation, you could:
        # 1. Combine with adjacent segments
        # 2. Add padding text
        # 3. Repeat parts of the text
        return text
    
    def _find_non_overlapping_window(self, start: float, end: float, used_timestamps: Set[Tuple[float, float]], max_duration: float) -> Tuple[Optional[float], Optional[float]]:
        """
        Find a non-overlapping window within a segment.
        
        Args:
            start: Original start time
            end: Original end time
            used_timestamps: Set of used timestamp ranges
            max_duration: Maximum duration for the window
            
        Returns:
            Tuple of (adjusted_start, adjusted_end) or (None, None) if no window found
        """
        # Try different windows within the segment
        segment_duration = end - start
        if segment_duration < 5.0:  # Too short to find a good window
            return None, None
        
        # Try windows of different sizes
        for window_duration in [max_duration, max_duration * 0.8, max_duration * 0.6, max_duration * 0.4]:
            if window_duration > segment_duration:
                continue
            
            # Try different start positions
            for offset in [0, 0.5, 1.0, 1.5, 2.0]:
                test_start = start + offset
                test_end = test_start + window_duration
                
                if test_end > end:
                    break
                
                if not self._has_overlap(test_start, test_end, used_timestamps):
                    return test_start, test_end
        
        return None, None
    
    def _build_15_second_quote(self, segments: List[Dict], start_index: int, target_duration: float) -> List[Dict]:
        """
        Build a quote of approximately target_duration by combining adjacent segments from the same speaker.
        
        Args:
            segments: List of all segments
            start_index: Index to start building the quote from
            target_duration: Target duration in seconds
            
        Returns:
            List of segments that make up the quote
        """
        if start_index >= len(segments):
            return []
        
        quote_segments = []
        current_speaker = segments[start_index].get('speaker_id', 'S1')
        start_time = segments[start_index]['start']
        target_end_time = start_time + target_duration
        
        # Add segments until we reach target duration or run out of same-speaker segments
        for i in range(start_index, len(segments)):
            segment = segments[i]
            segment_speaker = segment.get('speaker_id', 'S1')
            segment_start = segment['start']
            segment_end = segment['end']
            
            # Stop if we've reached a different speaker
            if segment_speaker != current_speaker:
                break
            
            # Stop if this segment would exceed our target duration
            if segment_start >= target_end_time:
                break
            
            quote_segments.append(segment)
            
            # If we've reached or exceeded target duration, we're done
            if segment_end >= target_end_time:
                break
        
        return quote_segments
    
    def _analyze_voice_inflection(self, audio_path: str, segments: List[Dict]) -> List[float]:
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
        
        Enhanced features for better excitement detection:
        - Energy (RMS): Higher volume indicates excitement (weight: 20%)
        - Spectral Centroid: Brighter/more excited sound (weight: 20%) 
        - Zero Crossing Rate: Rapid speech changes (weight: 15%)
        - Spectral Rolloff: High-frequency content (weight: 15%)
        - MFCC Variance: Timbre variation (weight: 15%)
        - Pitch Variation: Emotional expression (weight: 15%)
        
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
    
    def _calculate_classification_confidence(self, text: str, topic: str) -> float:
        """
        Calculate confidence score for topic classification.
        
        Args:
            text: Text that was classified
            topic: Assigned topic category
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        text_lower = text.lower()
        category_data = self.topic_categories.get(topic, {})
        
        # Count matches
        keyword_matches = sum(1 for keyword in category_data.get('keywords', []) if keyword in text_lower)
        pattern_matches = sum(1 for pattern in category_data.get('patterns', []) if re.search(pattern, text_lower))
        
        # Calculate confidence based on matches
        total_matches = keyword_matches + (pattern_matches * 2)  # Patterns weighted higher
        max_possible = len(category_data.get('keywords', [])) + (len(category_data.get('patterns', [])) * 2)
        
        if max_possible == 0:
            return 0.5  # Default confidence
        
        confidence = min(total_matches / max_possible, 1.0)
        return confidence
    
    def _select_with_topic_mix(self, candidates: List[AnimatedQuote]) -> List[AnimatedQuote]:
        """
        Select quotes with topic mix (30% each category).
        
        Args:
            candidates: List of candidate animated quotes
            
        Returns:
            Selected quotes with topic mix
        """
        selected_quotes = []
        used_timestamps = set()
        
        # Calculate target distribution (30% each = 3.6, so we'll use 4/4/4 = 33.3% each)
        target_counts = {
            'current_state': 4,
            'future_direction': 4,
            'products': 4
        }
        
        topic_counts = {'current_state': 0, 'future_direction': 0, 'products': 0}
        
        # First pass: select best quotes for each topic
        for quote in candidates:
            if topic_counts[quote.topic_category] < target_counts[quote.topic_category]:
                # Check for overlap with already selected quotes
                if not self._has_overlap(quote.start_timestamp, quote.end_timestamp, used_timestamps):
                    selected_quotes.append(quote)
                    topic_counts[quote.topic_category] += 1
                    used_timestamps.add((quote.start_timestamp, quote.end_timestamp))
                    
                    if len(selected_quotes) >= self.list2_count:
                        break
        
        # If we don't have enough quotes, fill with remaining best candidates
        if len(selected_quotes) < self.list2_count:
            for quote in candidates:
                if quote not in selected_quotes:
                    if not self._has_overlap(quote.start_timestamp, quote.end_timestamp, used_timestamps):
                        selected_quotes.append(quote)
                        used_timestamps.add((quote.start_timestamp, quote.end_timestamp))
                        if len(selected_quotes) >= self.list2_count:
                            break
        
        return selected_quotes
    
    def _quote_to_dict(self, quote: Quote) -> Dict:
        """
        Convert Quote object to dictionary for JSON output.
        
        Args:
            quote: Quote object
            
        Returns:
            Dictionary representation
        """
        return {
            'quote_text': quote.text,
            'start_ts': self.format_timestamp(quote.start_timestamp),
            'end_ts': self.format_timestamp(quote.end_timestamp),
            'duration_sec': quote.duration,
            'speaker_id': quote.speaker_id
        }
    
    def _animated_quote_to_dict(self, quote: AnimatedQuote) -> Dict:
        """
        Convert AnimatedQuote object to dictionary for JSON output.
        
        Args:
            quote: AnimatedQuote object
            
        Returns:
            Dictionary representation
        """
        return {
            'quote_text': quote.text,
            'topic_category': quote.topic_category.replace('_', ' ').title(),
            'excitement_score': round(quote.excitement_score, 3),
            'start_ts': self.format_timestamp(quote.start_timestamp),
            'end_ts': self.format_timestamp(quote.end_timestamp),
            'duration_sec': round(quote.duration, 1),
            'speaker_id': quote.speaker_id,
            'classification_confidence': round(quote.classification_confidence, 3)
        }
    
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
    
    def save_two_list_report(self, results: Dict, output_path: str):
        """
        Save two-list quotes to a formatted report.
        
        Args:
            results: Results dictionary with both lists
            output_path: Path to save the report
        """
        with open(str(output_path), 'w', encoding='utf-8') as f:
            f.write("Two-List Quote Detection Report\n")
            f.write("=" * 60 + "\n\n")
            
            # List 1
            list1 = results.get('list1_arbitrary_15s_quotes', [])
            f.write(f"LIST 1: Ten Arbitrary 15-Second Quotes ({len(list1)} found)\n")
            f.write("-" * 60 + "\n")
            f.write("Quote Text\tStart Timestamp\tEnd Timestamp\tDuration\tSpeaker ID\n")
            f.write("-" * 100 + "\n")
            
            for i, quote in enumerate(list1, 1):
                f.write(f'"{quote["quote_text"]}"\t{quote["start_ts"]}\t{quote["end_ts"]}\t{quote["duration_sec"]:.1f}s\t{quote["speaker_id"]}\n')
            
            f.write("\n" + "=" * 60 + "\n\n")
            
            # List 2
            list2 = results.get('list2_animated_quotes', [])
            f.write(f"LIST 2: Twelve Most Animated Quotes ({len(list2)} found)\n")
            f.write("-" * 60 + "\n")
            f.write("Quote Text\tTopic Category\tExcitement Score\tStart Timestamp\tEnd Timestamp\tDuration\tSpeaker ID\n")
            f.write("-" * 120 + "\n")
            
            for i, quote in enumerate(list2, 1):
                f.write(f'"{quote["quote_text"]}"\t{quote["topic_category"]}\t{quote["excitement_score"]}\t{quote["start_ts"]}\t{quote["end_ts"]}\t{quote["duration_sec"]:.1f}s\t{quote["speaker_id"]}\n')
            
            f.write("\n" + "=" * 60 + "\n")
            f.write("Topic Distribution (List 2):\n")
            
            topic_counts = {}
            for quote in list2:
                topic = quote['topic_category']
                topic_counts[topic] = topic_counts.get(topic, 0) + 1
            
            for topic, count in topic_counts.items():
                percentage = (count / len(list2)) * 100 if list2 else 0
                f.write(f"{topic}: {count} quotes ({percentage:.1f}%)\n")
        
        print(f"Two-list quotes report saved to: {output_path}")
