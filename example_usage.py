#!/usr/bin/env python3
"""
Example usage of the Local Media Transcription Tool
"""

from transcribe import MediaTranscriber
import os
from pathlib import Path


def example_single_file():
    """Example: Transcribe a single file"""
    print("=== Single File Transcription Example ===")
    
    transcriber = MediaTranscriber(model_size="base")
    
    # Example file path (replace with your actual file)
    file_path = "example_audio.mp3"
    
    if not os.path.exists(file_path):
        print(f"Example file {file_path} not found. Please provide a real file path.")
        return
    
    try:
        result = transcriber.transcribe_file(file_path, language="en")
        
        print(f"File: {result['file_path']}")
        print(f"Language: {result['language']}")
        print(f"Transcription:\n{result['text']}")
        
        # Save the result
        transcriber.save_transcription(result)
        
    except Exception as e:
        print(f"Error: {e}")


def example_batch_processing():
    """Example: Batch process multiple files"""
    print("\n=== Batch Processing Example ===")
    
    transcriber = MediaTranscriber(model_size="small")
    
    # Example directory (replace with your actual directory)
    directory = "example_media/"
    
    if not os.path.exists(directory):
        print(f"Example directory {directory} not found. Please provide a real directory path.")
        return
    
    # Find all supported files
    file_paths = []
    for file_path in Path(directory).rglob("*"):
        if file_path.is_file() and transcriber.is_supported_file(file_path):
            file_paths.append(str(file_path))
    
    if not file_paths:
        print("No supported media files found in the directory.")
        return
    
    print(f"Found {len(file_paths)} files to transcribe:")
    for fp in file_paths:
        print(f"  - {fp}")
    
    # Transcribe all files
    results = transcriber.transcribe_batch(file_paths, output_dir="transcriptions/")
    
    # Summary
    successful = len([r for r in results if 'error' not in r])
    failed = len(results) - successful
    
    print(f"\nBatch processing complete!")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")


def example_different_models():
    """Example: Compare different model sizes"""
    print("\n=== Model Comparison Example ===")
    
    file_path = "example_audio.mp3"
    
    if not os.path.exists(file_path):
        print(f"Example file {file_path} not found. Please provide a real file path.")
        return
    
    models = ["tiny", "base", "small"]
    
    for model_size in models:
        print(f"\n--- Using {model_size} model ---")
        
        transcriber = MediaTranscriber(model_size=model_size)
        
        try:
            result = transcriber.transcribe_file(file_path)
            print(f"Transcription ({model_size}): {result['text'][:100]}...")
            
        except Exception as e:
            print(f"Error with {model_size} model: {e}")


def example_language_detection():
    """Example: Language detection and translation"""
    print("\n=== Language Detection Example ===")
    
    transcriber = MediaTranscriber(model_size="base")
    
    file_path = "example_audio.mp3"
    
    if not os.path.exists(file_path):
        print(f"Example file {file_path} not found. Please provide a real file path.")
        return
    
    try:
        # Auto-detect language
        result = transcriber.transcribe_file(file_path)
        print(f"Detected language: {result['language']}")
        print(f"Transcription: {result['text']}")
        
        # Translate to English
        result_en = transcriber.transcribe_file(file_path, task="translate")
        print(f"\nTranslated to English: {result_en['text']}")
        
    except Exception as e:
        print(f"Error: {e}")


def example_animated_quotes():
    """Example: Animated quote detection"""
    print("\n=== Animated Quote Detection Example ===")
    
    transcriber = MediaTranscriber(model_size="base")
    
    file_path = "example_audio.mp3"
    
    if not os.path.exists(file_path):
        print(f"Example file {file_path} not found. Please provide a real file path.")
        return
    
    try:
        # Detect animated quotes
        result = transcriber.detect_animated_quotes(file_path, quote_duration=15.0, num_quotes=10)
        
        print(f"File: {result['file_path']}")
        print(f"Language: {result['language']}")
        print(f"Total segments: {len(result['segments'])}")
        
        # Display animated quotes
        if result.get('animated_quotes'):
            print(f"\nFound {len(result['animated_quotes'])} animated quotes:")
            print("-" * 60)
            
            for i, quote in enumerate(result['animated_quotes'], 1):
                start_time = transcriber.quote_detector.format_timestamp(quote.start_timestamp)
                end_time = transcriber.quote_detector.format_timestamp(quote.end_timestamp)
                
                print(f"\n{i}. [{start_time} - {end_time}] ({quote.topic_category})")
                print(f"   Animatedness Score: {quote.animatedness_score:.3f}")
                print(f"   Text: {quote.text}")
            
            # Save the results
            transcriber.save_transcription(result, "output/")
            transcriber.save_animated_quotes(result, "output/")
            
            # Show topic distribution
            topic_counts = {}
            for quote in result['animated_quotes']:
                topic_counts[quote.topic_category] = topic_counts.get(quote.topic_category, 0) + 1
            
            print(f"\nTopic Distribution:")
            for topic, count in topic_counts.items():
                print(f"  {topic}: {count} quotes")
        else:
            print("No animated quotes detected.")
        
    except Exception as e:
        print(f"Error: {e}")


def example_example_content():
    """Example: Processing enterprise content with animated quotes"""
    print("\n=== enterprise Content Processing Example ===")
    
    transcriber = MediaTranscriber(model_size="small")  # Use larger model for better accuracy
    
    file_path = "example_presentation.mp4"  # Replace with actual enterprise content
    
    if not os.path.exists(file_path):
        print(f"Example file {file_path} not found.")
        print("This example demonstrates processing enterprise content for animated quotes.")
        print("Replace 'example_presentation.mp4' with your actual enterprise video/audio file.")
        return
    
    try:
        # Process with animated quote detection
        result = transcriber.detect_animated_quotes(file_path, quote_duration=15.0, num_quotes=10)
        
        print(f"Processing enterprise content: {result['file_path']}")
        print(f"Language: {result['language']}")
        
        # Save comprehensive results
        transcriber.save_transcription(result, "example_output/")
        transcriber.save_animated_quotes(result, "example_output/")
        
        # Display summary
        if result.get('animated_quotes'):
            print(f"\nenterprise Animated Quotes Summary:")
            print(f"Total quotes found: {len(result['animated_quotes'])}")
            
            # Group by topic
            topics = {
                'current_state': [],
                'future_direction': [],
                'product_pipeline': []
            }
            
            for quote in result['animated_quotes']:
                topics[quote.topic_category].append(quote)
            
            for topic, quotes in topics.items():
                if quotes:
                    print(f"\n{topic.replace('_', ' ').title()} ({len(quotes)} quotes):")
                    for quote in quotes:
                        start_time = transcriber.quote_detector.format_timestamp(quote.start_timestamp)
                        print(f"  [{start_time}] Score: {quote.animatedness_score:.3f}")
                        print(f"  Text: {quote.text[:100]}...")
        
        print(f"\nResults saved to 'example_output/' directory")
        
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("Local Media Transcription Tool - Examples")
    print("=" * 50)
    
    # Run examples (comment out the ones you don't want to run)
    example_single_file()
    example_batch_processing()
    example_different_models()
    example_language_detection()
    example_animated_quotes()
    example_example_content()
    
    print("\n" + "=" * 50)
    print("Examples completed!")
    print("\nTo use with your own files:")
    print("1. Replace example file paths with your actual files")
    print("2. Run: python transcribe.py your_file.mp3")
    print("3. For animated quotes: python transcribe.py your_file.mp3 --animated-quotes")
    print("4. Or use the command line interface for batch processing")
    print("\nAnimated Quote Detection Features:")
    print("- Detects voice inflection indicating excitement")
    print("- Classifies content into enterprise topic categories")
    print("- Returns exactly 10 quotes with even topic distribution")
    print("- Each quote is exactly 15 seconds long")
    print("- Provides timestamps and animatedness scores")