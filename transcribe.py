#!/usr/bin/env python3
"""
Local Media Transcription Tool
Uses OpenAI Whisper for high-quality local transcription of audio and video files.
"""

import os
import sys
import click
import whisper
import ffmpeg
from pathlib import Path
from tqdm import tqdm
import json
from datetime import datetime
from animated_quotes import AnimatedQuoteDetector
from two_list_quotes import TwoListQuoteDetector

# Speaker detection: Try local first (no token needed), fallback to cloud-based
SPEAKER_DETECTION_AVAILABLE = False
LocalSpeakerDetector = None

try:
    from local_speaker_detection import LocalSpeakerDetector, format_speaker_stats
    SPEAKER_DETECTION_AVAILABLE = True
    print("✅ Local speaker detection loaded (no account needed!)")
except ImportError as e:
    print(f"⚠️  Local speaker detection not available: {e}")
    LocalSpeakerDetector = None
    format_speaker_stats = None


class MediaTranscriber:
    def __init__(self, model_size="base", enable_speaker_diarization=False):
        """
        Initialize the transcriber with a Whisper model.
        
        Args:
            model_size (str): Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            enable_speaker_diarization (bool): Enable AI-powered speaker diarization
        """
        self.model_size = model_size
        self.model = None
        self.supported_formats = {
            'audio': ['.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.wma'],
            'video': ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        }
        self.quote_detector = None
        self.two_list_detector = None
        self.speaker_diarizer = None
        self.enable_speaker_diarization = enable_speaker_diarization
        
        if enable_speaker_diarization:
            if SPEAKER_DETECTION_AVAILABLE and LocalSpeakerDetector:
                self.speaker_diarizer = LocalSpeakerDetector()
            else:
                click.echo("⚠️  Speaker diarization requested but not available.")
                click.echo("   Continuing with basic speaker detection.")
    
    def load_model(self):
        """Load the Whisper model, falling back to CPU if GPU runs out of memory."""
        if self.model is None:
            click.echo(f"Loading Whisper model '{self.model_size}'...")
            try:
                self.model = whisper.load_model(self.model_size)
            except RuntimeError as e:
                if "CUDA" in str(e) or "out of memory" in str(e):
                    click.echo(f"GPU out of memory, falling back to CPU...")
                    import torch
                    torch.cuda.empty_cache()
                    self.model = whisper.load_model(self.model_size, device="cpu")
                else:
                    raise
            click.echo("Model loaded successfully!")
    
    def load_quote_detector(self, quote_duration=15.0, num_quotes=10):
        """Load the animated quote detector."""
        if self.quote_detector is None:
            click.echo("Initializing animated quote detector...")
            self.quote_detector = AnimatedQuoteDetector(quote_duration, num_quotes)
            click.echo("Quote detector loaded successfully!")
    
    def load_two_list_detector(self, list1_duration=15.0, list1_count=10, 
                              list2_max_duration=15.0, list2_count=12):
        """Load the two-list quote detector."""
        if self.two_list_detector is None:
            click.echo("Initializing two-list quote detector...")
            self.two_list_detector = TwoListQuoteDetector(
                list1_duration, list1_count, list2_max_duration, list2_count
            )
            click.echo("Two-list detector loaded successfully!")
    
    def apply_speaker_diarization(self, result, audio_path, num_speakers=None, speaker_name_mapping=None):
        """
        Apply AI-powered speaker diarization to transcription result.
        
        Args:
            result: Transcription result dictionary
            audio_path: Path to audio file
            num_speakers: Expected number of speakers (optional)
            speaker_name_mapping: Dictionary mapping speaker IDs to names (optional)
            
        Returns:
            Updated result with speaker information
        """
        if not self.speaker_diarizer:
            return result
        
        try:
            # Perform diarization using LocalSpeakerDetector
            if result.get('segments'):
                result['segments'] = self.speaker_diarizer.diarize(
                    audio_path,
                    result['segments'],
                    num_speakers
                )
                
                # Apply speaker name mapping if provided
                if speaker_name_mapping:
                    # Apply the pre-built name mapping from main()
                    for segment in result['segments']:
                        if 'speaker_id' in segment and segment['speaker_id'] in speaker_name_mapping:
                            segment['speaker_id'] = speaker_name_mapping[segment['speaker_id']]
                    
                    # Print the mapping for user reference
                    click.echo(f"\n👥 Speaker Name Mapping Applied:")
                    for speaker_id, name in sorted(speaker_name_mapping.items()):
                        click.echo(f"   {speaker_id} → {name}")
                
                # Get speaker statistics
                speaker_counts = {}
                for segment in result['segments']:
                    if 'speaker_id' in segment:
                        speaker_id = segment['speaker_id']
                        speaker_counts[speaker_id] = speaker_counts.get(speaker_id, 0) + 1
                
                if speaker_counts:
                    click.echo(f"\n📊 Speaker Statistics:")
                    for speaker_id in sorted(speaker_counts.keys()):
                        click.echo(f"   {speaker_id}: {speaker_counts[speaker_id]} segments")
            
            return result
            
        except Exception as e:
            click.echo(f"⚠️  Speaker diarization failed: {e}")
            click.echo("   Continuing without speaker labels")
            return result
    
    def apply_basic_speaker_detection(self, result, num_speakers=None, speaker_name_mapping=None):
        """
        Apply basic speaker detection based on silence gaps and timing.
        
        Args:
            result: Transcription result dictionary
            num_speakers: Expected number of speakers (optional)
            speaker_name_mapping: Dictionary mapping speaker IDs to names
            
        Returns:
            Updated result with speaker IDs added to segments
        """
        if not result.get('segments'):
            return result
        
        segments = result['segments']
        current_speaker = 0
        last_end_time = 0
        silence_threshold = 2.0  # Seconds of silence that indicate speaker change
        
        # Add speaker IDs based on silence gaps
        for segment in segments:
            start_time = segment.get('start', 0)
            
            # If there's a significant gap, assume speaker changed
            if start_time - last_end_time > silence_threshold and last_end_time > 0:
                current_speaker = (current_speaker + 1) % (num_speakers if num_speakers else 10)
            
            # Assign speaker ID
            speaker_id = f"SPEAKER_{current_speaker:02d}"
            
            # Apply custom name if provided
            if speaker_name_mapping and speaker_id in speaker_name_mapping:
                segment['speaker_id'] = speaker_name_mapping[speaker_id]
            else:
                segment['speaker_id'] = speaker_id
            
            last_end_time = segment.get('end', 0)
        
        return result
    
    def is_supported_file(self, file_path):
        """Check if the file format is supported."""
        file_ext = Path(file_path).suffix.lower()
        all_formats = self.supported_formats['audio'] + self.supported_formats['video']
        return file_ext in all_formats
    
    def extract_audio(self, input_path, output_path=None):
        """
        Extract audio from video files or convert audio to WAV format using FFmpeg.
        
        Args:
            input_path (str): Path to input file
            output_path (str): Path for output audio file (optional)
        
        Returns:
            str: Path to the extracted/converted audio file
        """
        file_ext = Path(input_path).suffix.lower()
        
        if file_ext in self.supported_formats['audio'] + self.supported_formats['video']:
            # For both audio and video files, convert to WAV using FFmpeg
            if output_path is None:
                # Avoid overwriting the input file when it's already a .wav
                base = Path(input_path)
                output_path = str(base.parent / (base.stem + '_converted.wav'))

            try:
                (
                    ffmpeg
                    .input(input_path)
                    .output(output_path, acodec='pcm_s16le', ac=1, ar='16000')
                    .overwrite_output()
                    .run(quiet=True)
                )
                return output_path
            except ffmpeg.Error as e:
                raise Exception(f"Error extracting/converting audio: {e}")
        
        else:
            raise Exception(f"Unsupported file format: {file_ext}")
    
    def transcribe_file(self, file_path, language=None, task="transcribe"):
        """
        Transcribe a single media file.

        Args:
            file_path (str): Path to the media file
            language (str): Language code (optional, auto-detect if None)
            task (str): Task type ('transcribe' or 'translate')

        Returns:
            dict: Transcription result with text and metadata
        """
        file_path = str(file_path)
        if not self.is_supported_file(file_path):
            raise Exception(f"Unsupported file format: {Path(file_path).suffix}")
        
        self.load_model()
        
        click.echo(f"Processing: {Path(file_path).name}")
        
        # Extract audio if needed
        audio_path = self.extract_audio(file_path)
        
        try:
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_path,
                language=language,
                task=task,
                verbose=False
            )
            
            # Clean up temporary audio file if it was created
            if audio_path != file_path:
                os.remove(audio_path)
            
            return {
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'segments': result.get('segments', []),
                'file_path': file_path,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            # Clean up temporary audio file on error
            if audio_path != file_path and os.path.exists(audio_path):
                os.remove(audio_path)
            raise e
    
    def transcribe_batch(self, file_paths, language=None, task="transcribe", output_dir=None):
        """
        Transcribe multiple files in batch.
        
        Args:
            file_paths (list): List of file paths to transcribe
            language (str): Language code (optional)
            task (str): Task type ('transcribe' or 'translate')
            output_dir (str): Directory to save transcription files (optional)
        
        Returns:
            list: List of transcription results
        """
        results = []
        
        for file_path in tqdm(file_paths, desc="Transcribing files"):
            try:
                result = self.transcribe_file(file_path, language, task)
                results.append(result)
                
                # Save individual transcription if output directory specified
                if output_dir:
                    self.save_transcription(result, output_dir)
                
            except Exception as e:
                click.echo(f"Error transcribing {file_path}: {e}", err=True)
                results.append({
                    'file_path': file_path,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                })
        
        return results
    
    def save_transcription(self, result, output_dir=None):
        """
        Save transcription result to file.
        
        Args:
            result (dict): Transcription result
            output_dir (str): Output directory (optional)
        """
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        file_path = Path(result['file_path'])
        
        # Create output filename
        if output_dir:
            output_path = Path(output_dir) / f"{file_path.stem}_transcription.txt"
        else:
            output_path = file_path.parent / f"{file_path.stem}_transcription.txt"
        
        # Save as text file with sentence-level timestamps
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Transcription of: {file_path.name}\n")
            f.write(f"Language: {result.get('language', 'unknown')}\n")
            f.write(f"Timestamp: {result.get('timestamp', '')}\n")
            f.write("-" * 50 + "\n\n")
            
            # Format with sentence-level timestamps
            formatted_text = self._format_transcript_with_timestamps(result.get('segments', []))
            f.write(formatted_text)
        
        # Save detailed JSON (always, so /scan-outputs can find paired .txt/.json)
        json_path = output_path.with_suffix('.json')
        # Convert any Path objects to strings for JSON serialization
        json_result = {
            'text': result['text'],
            'language': result.get('language', 'unknown'),
            'segments': result.get('segments', []),
            'file_path': str(result.get('file_path', '')),
            'timestamp': result.get('timestamp', '')
        }
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(json_result, f, indent=2, ensure_ascii=False)
        
        click.echo(f"Transcription saved: {output_path}")
    
    def _format_transcript_with_timestamps(self, segments):
        """
        Format transcript with sentence-level timestamps and speaker changes.
        
        Args:
            segments: List of transcription segments with timestamps
            
        Returns:
            Formatted transcript string
        """
        if not segments:
            return "No segments available."
        
        formatted_lines = []
        last_end_time = 0
        
        for segment in segments:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            text = segment.get('text', '').strip()
            speaker_id = segment.get('speaker_id', None) or segment.get('speaker', None)
            
            # Check for speaker change (gap > 2 seconds indicates potential speaker change)
            if start_time - last_end_time > 2.0 and last_end_time > 0:
                # Add speaker change indicator (only if no speaker IDs exist)
                if not speaker_id:
                    formatted_lines.append(f"\n[Speaker Change - Gap: {start_time - last_end_time:.1f}s]")
            
            # Split text into sentences for better readability
            sentences = self._split_into_sentences(text)
            
            if len(sentences) == 1:
                # Single sentence - use segment timing
                formatted_lines.append(self._format_sentence_line([{
                    'text': sentences[0],
                    'start': start_time,
                    'end': end_time,
                    'speaker_id': speaker_id
                }]))
            else:
                # Multiple sentences - distribute time proportionally
                for i, sentence in enumerate(sentences):
                    if not sentence.strip():
                        continue
                    
                    sentence_start = start_time + (i * (end_time - start_time) / len(sentences))
                    sentence_end = start_time + ((i + 1) * (end_time - start_time) / len(sentences))
                    
                    formatted_lines.append(self._format_sentence_line([{
                        'text': sentence,
                        'start': sentence_start,
                        'end': sentence_end,
                        'speaker_id': speaker_id
                    }]))
            
            last_end_time = end_time
        
        return '\n'.join(formatted_lines)
    
    def _split_into_sentences(self, text):
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
    
    def _format_sentence_line(self, sentence_buffer):
        """
        Format a sentence with its timestamp and speaker ID if available.
        
        Args:
            sentence_buffer: List of sentence data
            
        Returns:
            Formatted line string
        """
        if not sentence_buffer:
            return ""
        
        # Combine all sentences in the buffer
        combined_text = ' '.join([s['text'] for s in sentence_buffer])
        
        # Use the timing of the first sentence
        start_time = sentence_buffer[0]['start']
        end_time = sentence_buffer[-1]['end']
        
        # Check if speaker ID is available
        speaker_id = sentence_buffer[0].get('speaker_id', None)
        
        # Format timestamp
        start_formatted = self._format_timestamp(start_time)
        end_formatted = self._format_timestamp(end_time)
        
        # Include speaker ID if available
        if speaker_id:
            return f"[{start_formatted} - {end_formatted}] {speaker_id}: {combined_text}"
        else:
            return f"[{start_formatted} - {end_formatted}] {combined_text}"
    
    def _format_timestamp(self, seconds):
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
    
    def detect_animated_quotes(self, file_path, quote_duration=15.0, num_quotes=10):
        """
        Detect animated quotes from a media file.

        Args:
            file_path (str): Path to the media file
            quote_duration (float): Duration of each quote in seconds
            num_quotes (int): Number of quotes to return

        Returns:
            dict: Result with transcription and animated quotes
        """
        file_path = str(file_path)
        if not self.is_supported_file(file_path):
            raise Exception(f"Unsupported file format: {Path(file_path).suffix}")
        
        self.load_model()
        self.load_quote_detector(quote_duration, num_quotes)
        
        click.echo(f"Processing: {Path(file_path).name}")
        
        # Extract audio if needed
        audio_path = self.extract_audio(file_path)
        
        try:
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_path,
                verbose=False
            )
            
            # Detect animated quotes
            click.echo("Detecting animated quotes...")
            quotes = self.quote_detector.detect_animated_quotes(audio_path, result)
            
            # Clean up temporary audio file if it was created
            if audio_path != file_path:
                os.remove(audio_path)
            
            # Convert quotes to dictionaries for JSON serialization
            quotes_data = []
            for quote in quotes:
                quotes_data.append({
                    'text': quote.text,
                    'topic_category': quote.topic_category,
                    'start_timestamp': float(quote.start_timestamp),
                    'end_timestamp': float(quote.end_timestamp),
                    'duration': float(quote.duration),
                    'animatedness_score': float(quote.animatedness_score),
                    'segment_index': quote.segment_index
                })
            
            return {
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'segments': result.get('segments', []),
                'animated_quotes': quotes_data,
                'file_path': file_path,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            # Clean up temporary audio file on error
            if audio_path != file_path and os.path.exists(audio_path):
                os.remove(audio_path)
            raise e
    
    def save_animated_quotes(self, result, output_dir=None):
        """
        Save animated quotes to files.
        
        Args:
            result (dict): Result with animated quotes
            output_dir (str): Output directory (optional)
        """
        if not result.get('animated_quotes'):
            return
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        file_path = Path(result['file_path'])
        
        # Create output filename
        if output_dir:
            quotes_path = Path(output_dir) / f"{file_path.stem}_animated_quotes.txt"
            json_path = Path(output_dir) / f"{file_path.stem}_animated_quotes.json"
        else:
            quotes_path = file_path.parent / f"{file_path.stem}_animated_quotes.txt"
            json_path = file_path.parent / f"{file_path.stem}_animated_quotes.json"
        
        # Save quotes report
        self.quote_detector.save_quotes_report(result['animated_quotes'], quotes_path)
        
        # Save quotes as JSON (quotes are already dictionaries)
        quotes_data = []
        for quote in result['animated_quotes']:
            quotes_data.append({
                'text': quote['text'],
                'topic_category': quote['topic_category'],
                'start_timestamp': float(quote['start_timestamp']),
                'end_timestamp': float(quote['end_timestamp']),
                'duration': float(quote['duration']),
                'animatedness_score': float(quote['animatedness_score']),
                'start_time_formatted': self.quote_detector.format_timestamp(quote['start_timestamp']),
                'end_time_formatted': self.quote_detector.format_timestamp(quote['end_timestamp'])
            })
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'file_path': str(result['file_path']),
                'timestamp': result['timestamp'],
                'quotes': quotes_data
            }, f, indent=2, ensure_ascii=False)
        
        click.echo(f"Animated quotes saved: {quotes_path}")
        click.echo(f"Animated quotes JSON saved: {json_path}")
    
    def detect_two_list_quotes(self, file_path, list1_duration=15.0, list1_count=10,
                              list2_max_duration=15.0, list2_count=12):
        """
        Detect two lists of quotes from a media file.

        Args:
            file_path (str): Path to the media file
            list1_duration (float): Duration of List 1 quotes in seconds
            list1_count (int): Number of quotes in List 1
            list2_max_duration (float): Maximum duration of List 2 quotes in seconds
            list2_count (int): Number of quotes in List 2

        Returns:
            dict: Result with transcription and two lists of quotes
        """
        file_path = str(file_path)
        if not self.is_supported_file(file_path):
            raise Exception(f"Unsupported file format: {Path(file_path).suffix}")
        
        self.load_model()
        self.load_two_list_detector(list1_duration, list1_count, list2_max_duration, list2_count)
        
        click.echo(f"Processing: {Path(file_path).name}")
        
        # Extract audio if needed
        audio_path = self.extract_audio(file_path)
        
        try:
            # Transcribe with Whisper
            result = self.model.transcribe(
                audio_path,
                verbose=False
            )
            
            # Detect two-list quotes
            click.echo("Detecting two-list quotes...")
            two_list_results = self.two_list_detector.detect_two_lists(audio_path, result)
            
            # Clean up temporary audio file if it was created
            if audio_path != file_path:
                os.remove(audio_path)
            
            return {
                'text': result['text'].strip(),
                'language': result.get('language', 'unknown'),
                'segments': result.get('segments', []),
                'two_list_quotes': two_list_results,
                'file_path': file_path,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            # Clean up temporary audio file on error
            if audio_path != file_path and os.path.exists(audio_path):
                os.remove(audio_path)
            raise e
    
    def save_two_list_quotes(self, result, output_dir=None):
        """
        Save two-list quotes to files.
        
        Args:
            result (dict): Result with two-list quotes
            output_dir (str): Output directory (optional)
        """
        if not result.get('two_list_quotes'):
            return
        
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        file_path = Path(result['file_path'])
        
        # Create output filenames
        if output_dir:
            report_path = Path(output_dir) / f"{file_path.stem}_two_list_quotes.txt"
            json_path = Path(output_dir) / f"{file_path.stem}_two_list_quotes.json"
        else:
            report_path = file_path.parent / f"{file_path.stem}_two_list_quotes.txt"
            json_path = file_path.parent / f"{file_path.stem}_two_list_quotes.json"
        
        # Save quotes report
        self.two_list_detector.save_two_list_report(result['two_list_quotes'], report_path)
        
        # Save quotes as JSON
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump({
                'file_path': str(result['file_path']),
                'timestamp': result['timestamp'],
                'two_list_quotes': result['two_list_quotes']
            }, f, indent=2, ensure_ascii=False)
        
        click.echo(f"Two-list quotes report saved: {report_path}")
        click.echo(f"Two-list quotes JSON saved: {json_path}")


@click.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--model', '-m', default='base', 
              type=click.Choice(['tiny', 'base', 'small', 'medium', 'large']),
              help='Whisper model size (default: base)')
@click.option('--language', '-l', default=None,
              help='Language code (e.g., en, es, fr). Auto-detect if not specified.')
@click.option('--task', '-t', default='transcribe',
              type=click.Choice(['transcribe', 'translate']),
              help='Task type: transcribe or translate to English')
@click.option('--output-dir', '-o', type=click.Path(),
              help='Output directory for transcription files')
@click.option('--batch', '-b', is_flag=True,
              help='Process all supported files in the input directory')
@click.option('--recursive', '-r', is_flag=True,
              help='Process files recursively in subdirectories (use with --batch)')
@click.option('--animated-quotes', '-q', is_flag=True,
              help='Detect animated quotes with voice inflection analysis')
@click.option('--quote-duration', default=15.0, type=float,
              help='Duration of each animated quote in seconds (default: 15.0)')
@click.option('--num-quotes', default=10, type=int,
              help='Number of animated quotes to return (default: 10)')
@click.option('--two-lists', '-2', is_flag=True,
              help='Generate two lists: List 1 (arbitrary quotes) and List 2 (animated quotes with topic mix)')
@click.option('--list1-count', default=10, type=int,
              help='Number of arbitrary quotes in List 1 (default: 10)')
@click.option('--list2-count', default=12, type=int,
              help='Number of animated quotes in List 2 (default: 12)')
@click.option('--speaker-diarization', '-s', is_flag=True,
              help='Enable AI-powered speaker diarization for accurate speaker detection')
@click.option('--num-speakers', type=int, default=None,
              help='Expected number of speakers (optional, auto-detect if not specified)')
@click.option('--speaker-names', type=str, default=None,
              help='Comma-separated speaker names (e.g., "Alice,Bob,Charlie")')
def main(input_path, model, language, task, output_dir, batch, recursive, animated_quotes, quote_duration, num_quotes, two_lists, list1_count, list2_count, speaker_diarization, num_speakers, speaker_names):
    """
    Transcribe media files using OpenAI Whisper.
    
    INPUT_PATH can be a single file or directory (with --batch flag).
    """
    transcriber = MediaTranscriber(model_size=model)
    
    input_path = Path(input_path)
    
    if batch or input_path.is_dir():
        # Batch processing
        if input_path.is_file():
            click.echo("Error: --batch flag requires a directory path", err=True)
            sys.exit(1)
        
        # Find all supported files
        file_paths = []
        pattern = "**/*" if recursive else "*"
        
        for file_path in input_path.glob(pattern):
            if file_path.is_file() and transcriber.is_supported_file(file_path):
                file_paths.append(str(file_path))
        
        if not file_paths:
            click.echo("No supported media files found in the directory.")
            return
        
        click.echo(f"Found {len(file_paths)} files to transcribe.")
        
        # Transcribe all files
        results = transcriber.transcribe_batch(file_paths, language, task, output_dir)
        
        # Summary
        successful = len([r for r in results if 'error' not in r])
        failed = len(results) - successful
        
        click.echo(f"\nTranscription complete!")
        click.echo(f"Successful: {successful}")
        click.echo(f"Failed: {failed}")
    
    else:
        # Single file processing
        if not input_path.is_file():
            click.echo("Error: Input path must be a file when not using --batch", err=True)
            sys.exit(1)

        if not transcriber.is_supported_file(input_path):
            click.echo(f"Error: Unsupported file format: {input_path.suffix}", err=True)
            sys.exit(1)
        
        # Process speaker names if provided
        speaker_name_mapping = {}
        if speaker_names:
            names = [n.strip() for n in speaker_names.split(',')]
            for i, name in enumerate(names):
                speaker_name_mapping[f'SPEAKER_{i:02d}'] = name
        
        try:
            # Initialize transcriber with speaker detection if requested
            if speaker_diarization:
                if SPEAKER_DETECTION_AVAILABLE:
                    click.echo("🎤 Local voice-based speaker detection enabled...")
                    transcriber = MediaTranscriber(model_size=model, enable_speaker_diarization=True)
                else:
                    click.echo("⚠️  Speaker detection not available, using basic detection")
                    transcriber = MediaTranscriber(model_size=model)
            else:
                transcriber = MediaTranscriber(model_size=model)
            
            if two_lists:
                # Detect two-list quotes
                result = transcriber.detect_two_list_quotes(input_path, 15.0, list1_count, 15.0, list2_count)
                
                # Apply speaker detection if enabled
                if speaker_diarization:
                    if transcriber.speaker_diarizer:
                        # Use AI-powered diarization
                        result = transcriber.apply_speaker_diarization(result, str(input_path), num_speakers, speaker_name_mapping)
                    else:
                        # Use basic silence-based detection
                        result = transcriber.apply_basic_speaker_detection(result, num_speakers, speaker_name_mapping)
                
                # Save transcription
                transcriber.save_transcription(result, output_dir)
                
                # Save two-list quotes if any were found
                if result.get('two_list_quotes'):
                    transcriber.save_two_list_quotes(result, output_dir)
                
                # Display result
                click.echo(f"\nTranscription ({result.get('language', 'unknown')}):")
                click.echo("-" * 50)
                click.echo(result['text'])
                
                # Display two-list quotes
                if result.get('two_list_quotes'):
                    two_list_data = result['two_list_quotes']
                    
                    # List 1
                    list1 = two_list_data.get('list1_arbitrary_15s_quotes', [])
                    click.echo(f"\nLIST 1: Arbitrary 15-Second Quotes ({len(list1)} found):")
                    click.echo("-" * 50)
                    for i, quote in enumerate(list1, 1):
                        click.echo(f"\n{i}. [{quote['start_ts']} - {quote['end_ts']}] ({quote['speaker_id']})")
                        click.echo(f"   Text: {quote['quote_text']}")
                    
                    # List 2
                    list2 = two_list_data.get('list2_animated_quotes', [])
                    click.echo(f"\nLIST 2: Animated Quotes with Topic Mix ({len(list2)} found):")
                    click.echo("-" * 50)
                    for i, quote in enumerate(list2, 1):
                        click.echo(f"\n{i}. [{quote['start_ts']} - {quote['end_ts']}] ({quote['topic_category']})")
                        click.echo(f"   Excitement Score: {quote['excitement_score']}")
                        click.echo(f"   Text: {quote['quote_text']}")
                else:
                    click.echo("\nNo two-list quotes detected.")
            
            elif animated_quotes:
                # Detect animated quotes
                result = transcriber.detect_animated_quotes(input_path, quote_duration, num_quotes)
                
                # Apply speaker detection if enabled
                if speaker_diarization:
                    if transcriber.speaker_diarizer:
                        # Use AI-powered diarization
                        result = transcriber.apply_speaker_diarization(result, str(input_path), num_speakers, speaker_name_mapping)
                    else:
                        # Use basic silence-based detection
                        result = transcriber.apply_basic_speaker_detection(result, num_speakers, speaker_name_mapping)
                
                # Save transcription
                transcriber.save_transcription(result, output_dir)
                
                # Save animated quotes if any were found
                if result.get('animated_quotes'):
                    transcriber.save_animated_quotes(result, output_dir)
                
                # Display result
                click.echo(f"\nTranscription ({result.get('language', 'unknown')}):")
                click.echo("-" * 50)
                click.echo(result['text'])
                
                # Display animated quotes
                if result.get('animated_quotes'):
                    click.echo(f"\nAnimated Quotes ({len(result['animated_quotes'])} found):")
                    click.echo("-" * 50)
                    for i, quote in enumerate(result['animated_quotes'], 1):
                        start_time = transcriber.quote_detector.format_timestamp(quote['start_timestamp'])
                        end_time = transcriber.quote_detector.format_timestamp(quote['end_timestamp'])
                        click.echo(f"\n{i}. [{start_time} - {end_time}] ({quote['topic_category']})")
                        click.echo(f"   Score: {quote['animatedness_score']:.3f}")
                        click.echo(f"   Text: {quote['text']}")
                else:
                    click.echo("\nNo animated quotes detected.")
            else:
                # Regular transcription
                result = transcriber.transcribe_file(input_path, language, task)
                
                # Apply speaker detection if enabled
                if speaker_diarization:
                    if transcriber.speaker_diarizer:
                        # Use AI-powered diarization
                        result = transcriber.apply_speaker_diarization(result, str(input_path), num_speakers, speaker_name_mapping)
                    else:
                        # Use basic silence-based detection
                        result = transcriber.apply_basic_speaker_detection(result, num_speakers, speaker_name_mapping)
                
                # Save transcription
                transcriber.save_transcription(result, output_dir)
                
                # Display result
                click.echo(f"\nTranscription ({result.get('language', 'unknown')}):")
                click.echo("-" * 50)
                click.echo(result['text'])
            
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            sys.exit(1)


if __name__ == '__main__':
    main()